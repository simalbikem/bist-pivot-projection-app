"""
İZOLASYON STRATEJİSİ:
    Testler gerçek data/bist_pivot.db dosyasına ASLA dokunmaz. 
    Her test, pytest'in tmp_path özelliğiyle oluşturulan GEÇİCİ ve BOŞ bir veritabanı dosyası kullanır. 
    monkeypatch ile database.py modülündeki DATABASE_PATH değişkeni, test süresince bu geçici dosyaya işaret edecek şekilde değiştirlir. 
    Test bitince pytest geçici dosyayı otomatik siler, kalıcı iz bırakılmaz.
"""
import pandas as pd
import pytest
import sqlite3
import database
from database import (
    create_tables,
    save_pivot_stats,
    save_confluence_zones,
    get_pivot_stats,
    get_confluence_zones,
)
from database import (
    create_tables, save_pivot_stats, save_confluence_zones,
    get_pivot_stats, get_confluence_zones,
    create_user, get_credentials_dict, get_user_id,
    create_alert, get_alerts_for_user, delete_alert, set_alert_active,
    get_all_active_alerts_with_contact, mark_alert_triggered,
    update_telegram_chat_id, get_telegram_chat_id,
    generate_link_code, verify_telegram_link,
    is_user_admin, get_all_users_with_stats, delete_user_and_data,
)

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Her testin kendi, boş ve geçici bir SQLite dosyasıyla çalışmasını sağlayan fixture. 
    Testler bunu parametre olarak alınca otomatik devreye girer."""
    test_db_path = tmp_path / "test_bist_pivot.db"
    monkeypatch.setattr(database, "DATABASE_PATH", str(test_db_path))
    create_tables()
    yield test_db_path

def test_create_tables_creates_file(temp_db):
    """create_tables çağrıldığında, veritabanı dosyasının gerçekten oluştuğu doğrulanır."""
    assert temp_db.exists()

def test_save_and_get_pivot_stats_roundtrip(temp_db):
    sample_stats = {
        "classic": {
            "PP": {
                "touch_probability": 0.5, "break_probability": None,
                "break_up_probability": 0.3, "break_down_probability": 0.2,
                "sample_size": 100,
            },
            "R1": {
                "touch_probability": 0.4, "break_probability": 0.1,
                "break_up_probability": None, "break_down_probability": None,
                "sample_size": 100,
            },
        }
    }

    save_pivot_stats("TEST.IS", sample_stats)
    df = get_pivot_stats("TEST.IS")

    assert len(df) == 2

    pp_row = df[df["level_name"] == "PP"].iloc[0]
    assert pp_row["touch_probability"] == pytest.approx(0.5)
    assert pd.isna(pp_row["break_probability"])
    assert pp_row["break_up_probability"] == pytest.approx(0.3)

    r1_row = df[df["level_name"] == "R1"].iloc[0]
    assert r1_row["break_probability"] == pytest.approx(0.1)
    assert pd.isna(r1_row["break_up_probability"])

def test_save_pivot_stats_overwrites_previous_data(temp_db):
    """Aynı ticker için save_pivot_stats iki kez çağrıldığında, eski
    verinin silinip yenisiyle değiştirildiği doğrulanır."""
    first_stats = {"classic": {"PP": {
        "touch_probability": 0.1, "break_probability": None,
        "break_up_probability": 0.1, "break_down_probability": 0.1,
        "sample_size": 50,
    }}}
    second_stats = {"classic": {"PP": {
        "touch_probability": 0.9, "break_probability": None,
        "break_up_probability": 0.9, "break_down_probability": 0.9,
        "sample_size": 999,
    }}}

    save_pivot_stats("TEST.IS", first_stats)
    save_pivot_stats("TEST.IS", second_stats)

    df = get_pivot_stats("TEST.IS")

    assert len(df) == 1  # çoğalmadı, hâlâ tek satır
    assert df.iloc[0]["touch_probability"] == pytest.approx(0.9)  # güncel veri
    assert df.iloc[0]["sample_size"] == 999

def test_save_and_get_confluence_zones_roundtrip(temp_db):
    """Bir confluence zone listesi kaydedilip JOIN ile geri okudunduğunda
    her contributorın doğru zone_id ile eşleştiği doğrulanır."""
    zones = [{
        "center": 101.91,
        "method_count": 3,
        "contributors": [
            {"method": "camarilla", "level": "S2", "value": 101.72},
            {"method": "classic", "level": "PP", "value": 102.0},
            {"method": "fibonacci", "level": "PP", "value": 102.0},
        ],
    }]

    save_confluence_zones("TEST.IS", zones)
    df = get_confluence_zones("TEST.IS")

    assert len(df) == 3  # her contributor için bir satır (JOIN davranışı)
    assert df["zone_id"].nunique() == 1  # hepsi aynı zone'a ait
    assert set(df["method"]) == {"camarilla", "classic", "fibonacci"}
    assert (df["method_count"] == 3).all()

def test_save_confluence_zones_overwrites_previous_data(temp_db):
    """Aynı ticker için save_confluence_zones iki kez çağrıldığında, eski zone ve 
    onun contributorslarının tamamen silinip yeni veriyle değiştirildiği doğrulanır."""
    old_zones = [{
        "center": 100.0, "method_count": 2,
        "contributors": [
            {"method": "classic", "level": "PP", "value": 100.0},
            {"method": "fibonacci", "level": "PP", "value": 100.1},
        ],
    }]
    new_zones = [{
        "center": 200.0, "method_count": 2,
        "contributors": [
            {"method": "woodie", "level": "R1", "value": 200.0},
            {"method": "demark", "level": "R1", "value": 200.1},
        ],
    }]

    save_confluence_zones("TEST.IS", old_zones)
    save_confluence_zones("TEST.IS", new_zones)

    df = get_confluence_zones("TEST.IS")

    assert len(df) == 2  # eski 2 satır değil, sadece yeni 2 satır
    assert set(df["method"]) == {"woodie", "demark"}  # eski yöntemler yok

# ---------------------------------------------------------
# Migration ve timeframe desteği testleri
# ---------------------------------------------------------
def test_migrate_add_timeframe_column_adds_missing_column(tmp_path, monkeypatch):
    """migrate_add_timeframe_column'ın, timeframe sütunu İÇERMEYEN eski şemalı bir tabloya bu sütunu doğru şekilde eklediğini doğrular."""
    test_db_path = tmp_path / "eski_sema.db"
    monkeypatch.setattr(database, "DATABASE_PATH", str(test_db_path))

    conn = sqlite3.connect(str(test_db_path))
    conn.execute("""
        CREATE TABLE pivot_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL, method TEXT NOT NULL, level_name TEXT NOT NULL,
            touch_probability REAL, break_probability REAL,
            break_up_probability REAL, break_down_probability REAL, sample_size INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE confluence_zones (
            zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL, center REAL NOT NULL, method_count INTEGER NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO pivot_stats (ticker, method, level_name, touch_probability, sample_size) "
        "VALUES ('ESKI.IS', 'classic', 'PP', 0.5, 100)"
    )
    conn.commit()
    conn.close()

    create_tables()

    conn = database.get_connection()
    cols = [row[1] for row in conn.execute("PRAGMA table_info(pivot_stats)").fetchall()]
    assert "timeframe" in cols

    eski_satir = conn.execute(
        "SELECT timeframe FROM pivot_stats WHERE ticker = 'ESKI.IS'"
    ).fetchone()
    assert eski_satir[0] == "daily"
    conn.close()

def test_migrate_add_timeframe_column_is_idempotent(temp_db):
    """migrate_add_timeframe_columnın art arda 2 kez çağrılmasının hata fırlatmadığını doğrular."""
    from database import migrate_add_timeframe_column

    migrate_add_timeframe_column()
    migrate_add_timeframe_column()

def test_save_and_get_pivot_stats_respects_timeframe(temp_db):
    """Aynı ticker için farklı timeframelerde kaydedilen verilerin birbirini SİLMEDİĞİNİ doğrular."""
    daily_stats = {"classic": {"PP": {
        "touch_probability": 0.5, "break_probability": None,
        "break_up_probability": 0.3, "break_down_probability": 0.2, "sample_size": 500,
    }}}
    weekly_stats = {"classic": {"PP": {
        "touch_probability": 0.7, "break_probability": None,
        "break_up_probability": 0.4, "break_down_probability": 0.3, "sample_size": 100,
    }}}

    save_pivot_stats("TEST.IS", daily_stats, timeframe="daily")
    save_pivot_stats("TEST.IS", weekly_stats, timeframe="weekly")

    daily_df = get_pivot_stats("TEST.IS", timeframe="daily")
    weekly_df = get_pivot_stats("TEST.IS", timeframe="weekly")

    assert len(daily_df) == 1
    assert len(weekly_df) == 1
    assert daily_df.iloc[0]["sample_size"] == 500
    assert weekly_df.iloc[0]["sample_size"] == 100

def test_save_and_get_confluence_zones_respects_timeframe(temp_db):
    """Confluence zoneların da timeframe bazında ayrı tutulduğunu doğrular."""
    daily_zones = [{"center": 100.0, "method_count": 2, "contributors": [
        {"method": "classic", "level": "PP", "value": 100.0},
        {"method": "fibonacci", "level": "PP", "value": 100.1},
    ]}]
    weekly_zones = [{"center": 200.0, "method_count": 3, "contributors": [
        {"method": "classic", "level": "R1", "value": 200.0},
        {"method": "fibonacci", "level": "R1", "value": 200.1},
        {"method": "woodie", "level": "R1", "value": 200.2},
    ]}]

    save_confluence_zones("TEST.IS", daily_zones, timeframe="daily")
    save_confluence_zones("TEST.IS", weekly_zones, timeframe="weekly")

    daily_df = get_confluence_zones("TEST.IS", timeframe="daily")
    weekly_df = get_confluence_zones("TEST.IS", timeframe="weekly")

    assert len(daily_df) == 2
    assert len(weekly_df) == 3
    assert (daily_df["timeframe"] == "daily").all()
    assert (weekly_df["timeframe"] == "weekly").all()

# ---------------------------------------------------------
# get_last_update_time testleri
# ---------------------------------------------------------
def test_get_last_update_time_returns_none_when_no_data(temp_db):
    """Hiç veri kaydedilmemiş bir ticker+timeframe için None dönmesi gerekir."""
    from database import get_last_update_time

    result = get_last_update_time("HIC_YOK.IS", timeframe="daily")

    assert result is None

def test_get_last_update_time_returns_timestamp_after_save(temp_db):
    """save_pivot_stats çağrıldıktan sonra, get_last_update_time'ın None olmayan bir zaman damgası döndürdüğünü doğrular."""
    from database import get_last_update_time

    sample_stats = {"classic": {"PP": {
        "touch_probability": 0.5, "break_probability": None,
        "break_up_probability": 0.3, "break_down_probability": 0.2, "sample_size": 100,
    }}}

    save_pivot_stats("TEST.IS", sample_stats, timeframe="daily")
    result = get_last_update_time("TEST.IS", timeframe="daily")

    assert result is not None
    # Format kontrolü: "YYYY-MM-DD HH:MM:SS" şeklinde olmalı
    assert len(result) == 19
    assert result[4] == "-" and result[7] == "-" and result[10] == " "

def test_get_last_update_time_updates_on_resave(temp_db):
    import time
    from database import get_last_update_time

    sample_stats = {"classic": {"PP": {
        "touch_probability": 0.5, "break_probability": None,
        "break_up_probability": 0.3, "break_down_probability": 0.2, "sample_size": 100,
    }}}

    save_pivot_stats("TEST.IS", sample_stats, timeframe="daily")
    ilk_zaman = get_last_update_time("TEST.IS", timeframe="daily")

    time.sleep(1.1)  # SQLite'ın saniye hassasiyetli CURRENT_TIMESTAMP'i için yeterli bekleme

    save_pivot_stats("TEST.IS", sample_stats, timeframe="daily")
    ikinci_zaman = get_last_update_time("TEST.IS", timeframe="daily")

    assert ikinci_zaman != ilk_zaman
    assert ikinci_zaman > ilk_zaman  # ISO formatlı string karşılaştırması kronolojik sıraya denk gelir

def test_get_last_update_time_is_independent_per_timeframe(temp_db):
    """Bir ticker'ın 'daily' verisi güncellendiğinde, aynı ticker'ın 'weekly' verisinin zaman damgasının ETKİLENMEDİĞİNİ doğrular 
    -timeframe bazlı izolasyonun bu fonksiyon için de geçerli olduğunukanıtlar."""
    import time
    from database import get_last_update_time

    sample_stats = {"classic": {"PP": {
        "touch_probability": 0.5, "break_probability": None,
        "break_up_probability": 0.3, "break_down_probability": 0.2, "sample_size": 100,
    }}}

    save_pivot_stats("TEST.IS", sample_stats, timeframe="weekly")
    weekly_zaman_once = get_last_update_time("TEST.IS", timeframe="weekly")

    time.sleep(1.1)

    save_pivot_stats("TEST.IS", sample_stats, timeframe="daily")
    weekly_zaman_sonra = get_last_update_time("TEST.IS", timeframe="weekly")

    assert weekly_zaman_once == weekly_zaman_sonra  # daily güncellemesi weekly'yi etkilememeli

def test_get_last_update_time_survives_schema_migration(tmp_path, monkeypatch):
    """Migration'dan geçmiş bir tabloda bile, yeni bir save_pivot_stats çağrısının doğru zaman damgası ürettiğini doğrular. 
    Bu, daha önce bulduğumuz ve düzelttiğimiz 'migration sonrası NULL kalma' hatasının kalıcı regresyon testidir."""
    import sqlite3
    from database import get_last_update_time

    test_db_path = tmp_path / "eski_sema_migration.db"
    monkeypatch.setattr(database, "DATABASE_PATH", str(test_db_path))

    conn = sqlite3.connect(str(test_db_path))
    conn.execute("""
        CREATE TABLE pivot_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL, method TEXT NOT NULL, level_name TEXT NOT NULL,
            timeframe TEXT NOT NULL DEFAULT 'daily',
            touch_probability REAL, break_probability REAL,
            break_up_probability REAL, break_down_probability REAL, sample_size INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE confluence_zones (
            zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL, timeframe TEXT NOT NULL DEFAULT 'daily',
            center REAL NOT NULL, method_count INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    create_tables()  # migrationlar tetiklenir

    sample_stats = {"classic": {"PP": {
        "touch_probability": 0.5, "break_probability": None,
        "break_up_probability": 0.3, "break_down_probability": 0.2, "sample_size": 100,
    }}}
    save_pivot_stats("YENI_KAYIT.IS", sample_stats, timeframe="daily")

    result = get_last_update_time("YENI_KAYIT.IS", timeframe="daily")

    assert result is not None 

# ---------------------------------------------------------
# create_user / get_credentials_dict testleri
# ---------------------------------------------------------
def test_create_user_rejects_duplicate_username(temp_db):
    assert create_user("dupuser", "Pass1234", "dup1@example.com", "Dup", "User") is True
    assert create_user("dupuser", "Pass5678", "dup2@example.com", "Dup2", "User2") is False

def test_create_user_rejects_duplicate_email(temp_db):
    assert create_user("uniqueuser1", "Pass1234", "same@example.com", "U1", "User") is True
    assert create_user("uniqueuser2", "Pass1234", "same@example.com", "U2", "User") is False

def test_get_credentials_dict_contains_hashed_password_not_plaintext(temp_db):
    create_user("hashcheck", "MySecretPass1", "hash@example.com", "Hash", "Check")
    creds = get_credentials_dict()
    stored_pw = creds["usernames"]["hashcheck"]["password"]
    assert stored_pw != "MySecretPass1"
    assert stored_pw.startswith("$2b$")  # bcrypt hash formati

# ---------------------------------------------------------
# alerts CRUD ve ownership testleri
# ---------------------------------------------------------
def test_create_alert_success_and_invalid_condition(temp_db):
    create_user("alertuser", "Pass1234", "alert@example.com", "Alert", "User")
    uid = get_user_id("alertuser")
    assert create_alert(uid, "THYAO.IS", "classic", "daily", "R1", "touch") is True
    with pytest.raises(ValueError):
        create_alert(uid, "THYAO.IS", "classic", "daily", "R1", "invalid")

def test_get_alerts_for_user_returns_only_own_alerts(temp_db):
    create_user("userX", "Pass1234", "x@example.com", "X", "User")
    create_user("userY", "Pass1234", "y@example.com", "Y", "User")
    uid_x = get_user_id("userX")
    uid_y = get_user_id("userY")
    create_alert(uid_x, "THYAO.IS", "classic", "daily", "R1", "touch")
    create_alert(uid_y, "AKBNK.IS", "classic", "daily", "PP", "break")

    x_alerts = get_alerts_for_user(uid_x)
    assert len(x_alerts) == 1
    assert x_alerts.iloc[0]["ticker"] == "THYAO.IS"

def test_delete_alert_ownership_enforced(temp_db):
    """Başka bir kullanıcının alertini silmeye çalışmak False dönmeli, gerçek sahibi silebilmeli."""
    create_user("owner", "Pass1234", "owner@example.com", "Owner", "User")
    create_user("intruder", "Pass1234", "intruder@example.com", "Intruder", "User")
    owner_id = get_user_id("owner")
    intruder_id = get_user_id("intruder")
    create_alert(owner_id, "THYAO.IS", "classic", "daily", "R1", "touch")
    alert_id = int(get_alerts_for_user(owner_id).iloc[0]["id"])

    assert delete_alert(alert_id, intruder_id) is False
    assert len(get_alerts_for_user(owner_id)) == 1  # hala duruyor

    assert delete_alert(alert_id, owner_id) is True
    assert len(get_alerts_for_user(owner_id)) == 0

def test_set_alert_active_ownership_enforced(temp_db):
    create_user("owner2", "Pass1234", "owner2@example.com", "Owner", "User")
    create_user("intruder2", "Pass1234", "intruder2@example.com", "Intruder", "User")
    owner_id = get_user_id("owner2")
    intruder_id = get_user_id("intruder2")
    create_alert(owner_id, "THYAO.IS", "classic", "daily", "R1", "touch")
    alert_id = int(get_alerts_for_user(owner_id).iloc[0]["id"])

    assert set_alert_active(alert_id, intruder_id, False) is False
    assert bool(get_alerts_for_user(owner_id).iloc[0]["active"]) is True

def test_get_all_active_alerts_with_contact_filters_correctly(temp_db):
    """Telegram bağlı olmayan kullanıcıların ve pasif alertlerin sonuçtan HARİÇ tutulduğunu doğrular."""
    create_user("withtg", "Pass1234", "withtg@example.com", "With", "TG")
    create_user("notg", "Pass1234", "notg@example.com", "No", "TG")
    uid_with = get_user_id("withtg")
    uid_without = get_user_id("notg")
    update_telegram_chat_id("withtg", "12345")

    create_alert(uid_with, "THYAO.IS", "classic", "daily", "R1", "touch")
    create_alert(uid_without, "AKBNK.IS", "classic", "daily", "PP", "touch")  # telegram yok

    create_alert(uid_with, "AKBNK.IS", "classic", "daily", "PP", "break")
    paused_id = int(
        get_alerts_for_user(uid_with)[get_alerts_for_user(uid_with)["ticker"] == "AKBNK.IS"].iloc[0]["id"]
    )
    set_alert_active(paused_id, uid_with, False)

    active_df = get_all_active_alerts_with_contact()
    assert list(active_df["ticker"]) == ["THYAO.IS"]  # sadece aktif + telegram bağlı olan

def test_mark_alert_triggered_updates_date(temp_db):
    create_user("trigu", "Pass1234", "trigu@example.com", "Trig", "User")
    uid = get_user_id("trigu")
    create_alert(uid, "THYAO.IS", "classic", "daily", "R1", "touch")
    alert_id = int(get_alerts_for_user(uid).iloc[0]["id"])

    assert get_alerts_for_user(uid).iloc[0]["last_triggered_date"] is None
    mark_alert_triggered(alert_id, "2026-09-02")
    assert get_alerts_for_user(uid).iloc[0]["last_triggered_date"] == "2026-09-02"

# ---------------------------------------------------------
# Telegram bağlantı kodu testleri (requests.get mock'lu)
# ---------------------------------------------------------
def test_generate_link_code_returns_and_stores_code(temp_db):
    create_user("linkuser", "Pass1234", "link@example.com", "Link", "User")
    code = generate_link_code("linkuser")
    assert code.startswith("BIST-")

    conn = database.get_connection()
    stored = conn.execute(
        "SELECT pending_link_code FROM users WHERE username='linkuser'"
    ).fetchone()[0]
    conn.close()
    assert stored == code

def test_verify_telegram_link_success(temp_db, monkeypatch):
    create_user("linkuser2", "Pass1234", "link2@example.com", "Link", "User")
    code = generate_link_code("linkuser2")

    class FakeResponse:
        def json(self):
            return {"ok": True, "result": [{"message": {"chat": {"id": 999888777}, "text": code}}]}

    monkeypatch.setattr("requests.get", lambda url, timeout=10: FakeResponse())

    assert verify_telegram_link("linkuser2") is True
    assert get_telegram_chat_id("linkuser2") == "999888777"

def test_verify_telegram_link_code_not_found(temp_db, monkeypatch):
    create_user("linkuser3", "Pass1234", "link3@example.com", "Link", "User")
    generate_link_code("linkuser3")

    class FakeResponse:
        def json(self):
            return {"ok": True, "result": []}

    monkeypatch.setattr("requests.get", lambda url, timeout=10: FakeResponse())

    assert verify_telegram_link("linkuser3") is False

# ---------------------------------------------------------
# Admin / kullanıcı silme testleri
# ---------------------------------------------------------
def test_is_user_admin_default_false_and_after_promotion(temp_db):
    create_user("plainuser", "Pass1234", "plain@example.com", "Plain", "User")
    assert is_user_admin("plainuser") is False

    conn = database.get_connection()
    conn.execute("UPDATE users SET is_admin = 1 WHERE username = 'plainuser'")
    conn.commit()
    conn.close()
    assert is_user_admin("plainuser") is True

def test_get_all_users_with_stats_counts_correctly(temp_db):
    create_user("statsuser", "Pass1234", "stats@example.com", "Stats", "User")
    uid = get_user_id("statsuser")
    update_telegram_chat_id("statsuser", "555")
    create_alert(uid, "THYAO.IS", "classic", "daily", "R1", "touch")
    create_alert(uid, "AKBNK.IS", "classic", "daily", "PP", "touch")

    df = get_all_users_with_stats()
    row = df[df["username"] == "statsuser"].iloc[0]
    assert row["alert_count"] == 2
    assert row["telegram_connected"] == 1

def test_delete_user_and_data_cascades(temp_db):
    """Bir kullanıcı silindiğinde SADECE onun alertleri silinmeli, başkasınınkiler kalmalı."""
    create_user("todelete", "Pass1234", "todelete@example.com", "To", "Delete")
    create_user("survivor", "Pass1234", "survivor@example.com", "Sur", "Vivor")
    uid_delete = get_user_id("todelete")
    uid_survivor = get_user_id("survivor")

    create_alert(uid_delete, "THYAO.IS", "classic", "daily", "R1", "touch")
    create_alert(uid_survivor, "AKBNK.IS", "classic", "daily", "PP", "touch")

    assert delete_user_and_data(uid_delete) is True

    creds = get_credentials_dict()
    assert "todelete" not in creds["usernames"]
    assert "survivor" in creds["usernames"]

    conn = database.get_connection()
    remaining = conn.execute("SELECT ticker FROM alerts").fetchall()
    conn.close()
    assert remaining == [("AKBNK.IS",)]

def test_delete_user_and_data_nonexistent_returns_false(temp_db):
    assert delete_user_and_data(999999) is False

# ---------------------------------------------------------
# Migration idempotency testleri (is_admin, pending_link_code)
# ---------------------------------------------------------
def test_migrate_add_is_admin_column_is_idempotent(temp_db):
    from database import migrate_add_is_admin_column
    migrate_add_is_admin_column()
    migrate_add_is_admin_column()  # ikinci çağrı hata vermemeli

def test_migrate_add_pending_link_code_column_is_idempotent(temp_db):
    from database import migrate_add_pending_link_code_column
    migrate_add_pending_link_code_column()
    migrate_add_pending_link_code_column()
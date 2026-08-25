"""
İZOLASYON STRATEJİSİ:
    Testler gerçek data/bist_pivot.db dosyasına ASLA dokunmaz. 
    Her test, pytest'in tmp_path özelliğiyle oluşturulan GEÇİCİ ve BOŞ bir veritabanı dosyası kullanır. 
    monkeypatch ile database.py modülündeki DATABASE_PATH değişkeni, test süresince bu geçici dosyaya işaret edecek şekilde değiştirlir. 
    Test bitince pytest geçici dosyayı otomatik siler, kalıcı iz bırakılmaz.
"""
import pandas as pd
import pytest

import database
from database import (
    create_tables,
    save_pivot_stats,
    save_confluence_zones,
    get_pivot_stats,
    get_confluence_zones,
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
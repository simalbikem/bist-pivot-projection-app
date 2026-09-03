from dotenv import load_dotenv
import os
import libsql

load_dotenv()

conn = libsql.connect(
    database=os.getenv("TURSO_DATABASE_URL"),
    auth_token=os.getenv("TURSO_AUTH_TOKEN"),
)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS fix_test_users")
cursor.execute("DROP TABLE IF EXISTS fix_test_alerts")
conn.commit()
cursor.execute("CREATE TABLE fix_test_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE)")
cursor.execute("CREATE TABLE fix_test_alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ticker TEXT)")
conn.commit()

print("=== TEST 1: create_user mantigi (SELECT-once kontrolu) ===")
def fake_create_user(username):
    cursor.execute("SELECT 1 FROM fix_test_users WHERE username = ?", (username,))
    if cursor.fetchone() is not None:
        return False
    cursor.execute("INSERT INTO fix_test_users (username) VALUES (?)", (username,))
    conn.commit()
    return True

sonuc1 = fake_create_user("aynikullanici")
sonuc2 = fake_create_user("aynikullanici")  # tekrar -False dönmeli
print(f"Ilk kayit: {sonuc1} (True olmali)")
print(f"Tekrar kayit: {sonuc2} (False olmali)")
assert sonuc1 is True and sonuc2 is False
print("BASARILI\n")

print("=== TEST 2: delete_alert mantigi (SELECT-once kontrolu, rowcount YOK) ===")
cursor.execute("INSERT INTO fix_test_users (username) VALUES ('owner')")
conn.commit()
owner_id = cursor.lastrowid
cursor.execute("INSERT INTO fix_test_alerts (user_id, ticker) VALUES (?, 'THYAO.IS')", (owner_id,))
conn.commit()
alert_id = cursor.lastrowid

def fake_delete_alert(aid, uid):
    cursor.execute("SELECT 1 FROM fix_test_alerts WHERE id = ? AND user_id = ?", (aid, uid))
    exists = cursor.fetchone() is not None
    if exists:
        cursor.execute("DELETE FROM fix_test_alerts WHERE id = ? AND user_id = ?", (aid, uid))
        conn.commit()
    return exists

# Yanlış kullanıcıyla silmeyi dene -False dönmeli, silinmemeli
yanlis_sonuc = fake_delete_alert(alert_id, 99999)
print(f"Yanlis kullaniciyla silme: {yanlis_sonuc} (False olmali)")
kalan = cursor.execute("SELECT COUNT(*) FROM fix_test_alerts").fetchone()[0]
print(f"Silme sonrasi kalan alert sayisi: {kalan} (1 olmali, silinmemis olmali)")

# Dogru kullanıcıyla sil -True dönmeli
dogru_sonuc = fake_delete_alert(alert_id, owner_id)
print(f"Dogru kullaniciyla silme: {dogru_sonuc} (True olmali)")
kalan2 = cursor.execute("SELECT COUNT(*) FROM fix_test_alerts").fetchone()[0]
print(f"Silme sonrasi kalan alert sayisi: {kalan2} (0 olmali)")

assert yanlis_sonuc is False and kalan == 1
assert dogru_sonuc is True and kalan2 == 0
print("BASARILI\n")

cursor.execute("DROP TABLE fix_test_users")
cursor.execute("DROP TABLE fix_test_alerts")
conn.commit()
print("Temizlik tamamlandi. TUM DUZELTMELER TURSO'DA DOGRULANDI.")
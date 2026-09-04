from dotenv import load_dotenv
import os
import libsql

load_dotenv()

# DIKKAT: Bu script BILEREK dogrudan libsql kullaniyor (get_connection()
# uzerinden degil), .env'deki USE_TURSO durumundan BAGIMSIZ olarak
# gercekten production Turso'ya baglaniyoruz.
conn = libsql.connect(
    database=os.getenv("TURSO_DATABASE_URL"),
    auth_token=os.getenv("TURSO_AUTH_TOKEN"),
)
cursor = conn.cursor()

# Sadece dogrulanmis test kirliligi olan kullanici ID'leri - manuel olarak
# incelenip onaylanmistir (testuser, balbademvanilya, cevizlisucuk, biricik
# haric tutulmustur).
KIRLILIK_ID_LISTESI = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28]

print(f"{len(KIRLILIK_ID_LISTESI)} kullanici silinecek.\n")

for user_id in KIRLILIK_ID_LISTESI:
    # Once o kullanicinin gercekten var oldugunu ve dogru kullanici oldugunu
    # teyit edelim (guvenlik icin, yanlislikla farkli bir ID'yi silmeyelim).
    row = cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        print(f"  UYARI: id={user_id} zaten yok, atlaniyor.")
        continue

    username = row[0]
    cursor.execute("DELETE FROM alerts WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    print(f"  Silindi: id={user_id}, username={username}")

print("\n=== TEMIZLIK SONRASI KONTROL ===")
remaining_users = cursor.execute("SELECT id, username FROM users ORDER BY id").fetchall()
print(f"Kalan kullanici sayisi: {len(remaining_users)}")
for u in remaining_users:
    print(f"  {u}")

remaining_alerts = cursor.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
print(f"\nKalan alert sayisi: {remaining_alerts}")

# Sahipsiz (orphan) alert kaldi mi kontrolu
orphans = cursor.execute("""
    SELECT a.id FROM alerts a
    LEFT JOIN users u ON a.user_id = u.id
    WHERE u.id IS NULL
""").fetchall()
print(f"Sahipsiz alert sayisi (0 olmali): {len(orphans)}")
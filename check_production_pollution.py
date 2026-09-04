from dotenv import load_dotenv
import os
import libsql

load_dotenv()

conn = libsql.connect(
    database=os.getenv("TURSO_DATABASE_URL"),
    auth_token=os.getenv("TURSO_AUTH_TOKEN"),
)

print("=== TUM KULLANICILAR ===")
users = conn.execute("SELECT id, username, email, created_at FROM users ORDER BY created_at").fetchall()
for u in users:
    print(f"  {u}")
print(f"\nToplam kullanici sayisi: {len(users)}")

print("\n=== TUM ALERTLER (sadece ticker + kullanici) ===")
alerts = conn.execute("""
    SELECT a.id, u.username, a.ticker, a.created_at
    FROM alerts a JOIN users u ON a.user_id = u.id
    ORDER BY a.created_at
""").fetchall()
for a in alerts:
    print(f"  {a}")
print(f"\nToplam alert sayisi: {len(alerts)}")
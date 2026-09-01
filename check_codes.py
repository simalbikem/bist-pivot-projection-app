from database import get_connection

conn = get_connection()
rows = conn.execute("SELECT username, pending_link_code, telegram_chat_id FROM users").fetchall()
conn.close()

print("Tum kullanicilarin durumu:")
for username, code, chat_id in rows:
    print(f"  {username}: pending_link_code={code}, telegram_chat_id={chat_id}")
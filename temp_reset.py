from database import get_connection

conn = get_connection()
conn.execute("UPDATE users SET telegram_chat_id = NULL WHERE username = 'testuser'")
conn.commit()
conn.close()
print("testuser telegram_chat_id temizlendi.")
"""
Telegram Bot API üzerinden kullanıcılara bildirim mesajı gönderir.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def send_telegram_message(chat_id: str, text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        print("HATA: TELEGRAM_BOT_TOKEN .env dosyasında bulunamadı.")
        return False

    try:
        response = requests.post(
            TELEGRAM_API_URL,
            data={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        result = response.json()

        if result.get("ok"):
            return True
        else:
            print(f"HATA: Telegram mesajı gönderilemedi: {result.get('description')}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"HATA: Telegram API'sine bağlanılamadı: {e}")
        return False

# Hızlı test
if __name__ == "__main__":
    from database import get_telegram_chat_id

    test_chat_id = get_telegram_chat_id("testuser")

    if test_chat_id is None:
        print("testuser'ın kayıtlı bir telegram_chat_id'si yok.")
    else:
        basarili = send_telegram_message(
            test_chat_id,
            "🎉 The BIST Pivot Alert Bot connection was successful! This is a test message."
        )
        print("Mesaj gönderildi mi:", basarili)
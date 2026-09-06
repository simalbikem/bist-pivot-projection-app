# 📊 BIST Pivot-Point Based Stock Projection Tool
Borsa İstanbul (BIST100) hisseleri için pivot-nokta tabanlı teknik analiz, confluence (kesişim bölgesi) tespiti, geçmiş performans istatistikleri ve gerçek zamanlı Telegram bildirimleri sunan çok kullanıcılı bir web uygulamasıdır.

🔗 **Canlı Demo:** [bist-pivot-projection-app.streamlit.app](https://bist-pivot-projection-app.streamlit.app/)
> ⚠️ **Yasal Uyarı:** Bu sistem yatırım tavsiyesi vermez. Pivot seviyeleri istatistiksel olarak hesaplanmış potansiyel destek/direnç bölgeleridir, kesin fiyat garantisi sunmaz.

---

## 🚀 Özellikler
- **5 Pivot Yöntemi:** Classic, Fibonacci, Camarilla, DeMark, Woodie — formüller harici kaynaklarla doğrulanmıştır.
- **Confluence Analizi:** Farklı yöntemlerin birbirine yakın düştüğü, istatistiksel olarak güçlü destek/direnç bölgelerinin tespiti yapılabilmektedir.
- **Backtest İstatistikleri:** Her seviye için geçmiş "touch" ve "break" olasılıkları, yönlü PP kırılma ayrımı dahil edilmiştir.
- **Çoklu Zaman Dilimi:** Günlük, haftalık, aylık analiz desteği bulunmaktadır.
- **BIST100:** Tüm endeks bileşenleri için veriler otomatik güncellenmektedir.
- **Screener:** Touch/break olasılığına veya confluence gücüne göre hisseler taranabilmektedir.
- **Çok Kullanıcılı Sistem:** Güvenli kayıt/giriş (bcrypt şifreleme) ve kişiselleştirilmiş alert yönetimini kapsar.
- **Telegram Alert Sistemi:** Kullanıcı dostu bağlantı akışı, seçilen hisse/seviye/koşul gerçekleştiğinde otomatik bildirim sağlanmaktadır.
- **Admin Paneli:** Kullanıcı yönetimi ve kapsamlı istatistikler sunar.

---

## 🛠️ Teknoloji Yığını
| Katman | Teknoloji |
|---|---|
| Arayüz | Streamlit |
| Veri Kaynağı | yfinance (Yahoo Finance) |
| Veritabanı | SQLite (yerel) / Turso (canlı, SQLite uyumlu bulut) |
| Kimlik Doğrulama | streamlit-authenticator (bcrypt) |
| Bildirimler | Telegram Bot API |
| Otomasyon | GitHub Actions (zamanlanmış veri güncelleme + alert kontrolü) |
| Test | pytest (100+ test) |
| Görselleştirme | Plotly |

---

## 📁 Proje Yapısı

├── app.py #Streamlit ana uygulama

├── config.py #Ayarlar, ortam değişkenleri

├── data_fetcher.py #yfinance veri çekme, resampling

├── pivot_calculations.py #5 pivot yöntemi hesaplama motoru

├── confluence.py #Kesişim bölgesi tespiti

├── backtester.py #Touch/break istatistik motoru

├── database.py #SQLite/Turso veritabanı katmanı

├── notifications.py #Telegram "Alert" gönderimi

├── alert_checker.py #Alert kontrol scripti (GitHub Actions ile otomatik)

├── update_data.py #Backtest/confluence veri güncelleme scripti

├── charts.py #Plotly grafik üretimi

├── tests/ #pytest test paketi

└── .github/workflows/ #Otomatik veri güncelleme ve alert kontrolü

---

## ⚙️ Yerel Kurulum

**1. Depoyu klonlayın:**
```bash
git clone https://github.com/simalbikem/bist-pivot-projection-app.git
cd bist-pivot-projection-app
```

**2. Sanal ortam oluşturun ve etkinleştirin:**
```bash
python -m venv venv
venv\Scripts\Activate.ps1   # Windows
source venv/bin/activate    # macOS/Linux
```

**3. Bağımlılıkları kurun:**
```bash
pip install -r requirements.txt
```

**4. `.env` dosyası oluşturun:**
```bash
COOKIE_KEY=<rastgele_güvenli_bir_anahtar>
TELEGRAM_BOT_TOKEN=<telegram_bot_tokeniniz>
USE_TURSO=false
```
> `USE_TURSO=false` iken uygulama yerel SQLite dosyasını (`data/bist_pivot.db`) kullanır. Buluta bağlanmak isterseniz `USE_TURSO=true` yapıp `TURSO_DATABASE_URL` ve `TURSO_AUTH_TOKEN` değerlerini de ekleyin.

**5. Hisse verilerini ve backtest istatistiklerini oluşturun:**
```bash
python update_data.py
```

**6. Uygulamayı başlatın:**
```bash
streamlit run app.py
```

---

## 🧪 Testler
```bash
pytest tests/ -v
```
100+ test, tüm çekirdek modülleri (pivot hesaplama, confluence, backtest, veritabanı, alert sistemi) kapsar. Testler her zaman izole yerel veritabanı üzerinde çalışır, canlı/production verisine asla dokunmaz.

---

## 🤖 Otomasyon
Proje, GitHub Actions ile iki zamanlanmış görev çalıştırır:
- **Update Data:** Her gün piyasa kapanışından sonra, 100 hissenin backtest ve confluence verilerini yeniler.
- **Alert Checker:** Piyasanın açık olduğu saatlerde 15 dakikada bir, kullanıcı alertlerini kontrol edip gerektiğinde Telegram bildirimi gönderir.

---

## 👤 Geliştirici
**Şimal Bikem CEYLAN**

Yalova Üniversitesi | Bilgisayar Mühendisliği

---

## 📄 Lisans
Bu proje bahsi geçen şahısın **Türkiye Vakıflar Bankası T.A.O. | İzleme ve Takip Uygulama Geliştirme Departmanı | Zorunlu Üniversite Stajı** kapsamında geliştirilmiştir.
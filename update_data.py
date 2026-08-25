"""
Bu script Streamlit arayüzünden ayrı tutulmaktadır, çünkü:
    - Backtest hesaplaması (2 yıllık veri x 8 hisse) birkaç dakika sürebilir.
    - Streamlit her açıldığında bunu yeniden hesaplamak kullanıcı deneyimini yavaşlatır.
    - Verinin ne zaman güncellenebileceği kontrol edilebilir.
"""
from config import BIST_STOCKS
from data_fetcher import get_stock_data
from pivot_calculations import calculate_all_pivots
from confluence import find_confluence_zones
from backtester import backtest_stock
from database import create_tables, save_pivot_stats, save_confluence_zones

def update_single_stock(ticker: str) -> bool:
    """Tek bir hisse için backtest + confluence hesaplanıp kayıt edilir."""
    print(f"\n{'='*50}")
    print(f"{ticker} işleniyor...")
    print(f"{'='*50}")

    # --- 1. Backtest ---
    stats = backtest_stock(ticker)
    if not stats:
        print(f"  UYARI: {ticker} için backtest verisi yok, atlanıyor.")
        return False

    save_pivot_stats(ticker, stats)
    print(f"  ✓ Backtest kaydedildi ({sum(len(v) for v in stats.values())} seviye)")

    # --- 2. Confluence (son günün pivotlarıyla) ---
    df = get_stock_data(ticker)
    if df.empty or len(df) < 2:
        print(f"  UYARI: {ticker} için confluence hesaplanamadı (yetersiz veri).")
        return True  # backtest zaten kaydedildi, kısmi başarı sayılır

    prev_row = df.iloc[-2]
    today_row = df.iloc[-1]

    pivots = calculate_all_pivots(
        prev_open=prev_row["Open"], prev_high=prev_row["High"],
        prev_low=prev_row["Low"], prev_close=prev_row["Close"],
        today_open=today_row["Open"],
    )
    zones = find_confluence_zones(pivots)
    save_confluence_zones(ticker, zones)
    print(f"  ✓ Confluence kaydedildi ({len(zones)} zone bulundu)")

    return True

def update_all_stocks():
    """BIST_STOCKS listesindeki tüm hisseleri sırayla günceller."""
    create_tables()  # tablolar yoksa oluşturur, varsa dokunmaz

    basarili = []
    basarisiz = []

    for ticker in BIST_STOCKS:
        try:
            if update_single_stock(ticker):
                basarili.append(ticker)
            else:
                basarisiz.append(ticker)
        except Exception as e:
            print(f"  HATA: {ticker} işlenirken beklenmeyen bir sorun oluştu: {e}")
            basarisiz.append(ticker)

    print(f"\n{'='*50}")
    print("ÖZET")
    print(f"{'='*50}")
    print(f"Başarılı: {len(basarili)}/{len(BIST_STOCKS)} -> {basarili}")
    if basarisiz:
        print(f"Başarısız: {basarisiz}")

if __name__ == "__main__":
    update_all_stocks()
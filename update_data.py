import time
from datetime import datetime

from config import BIST_STOCKS, TIMEFRAMES
from data_fetcher import get_stock_data, resample_to_timeframe
from pivot_calculations import calculate_all_pivots
from confluence import find_confluence_zones
from backtester import backtest_stock
from database import create_tables, save_pivot_stats, save_confluence_zones, get_admin_chat_ids
from notifications import send_telegram_message

def update_single_stock_timeframe(ticker: str, timeframe: str, raw_df) -> bool:
    """Tek bir hisse + tek bir zaman dilimi için backtest + confluence değerini hesaplayıp kaydeder.
    raw_df: ticker için önceden çekilmiş HAM GÜNLÜK veri 
    -bu fonksiyon kendisi hiç yfinance çağırmaz, dışarıdan verilen veriyi kullanır."""
    stats = backtest_stock(ticker, timeframe=timeframe, raw_df=raw_df)
    if not stats:
        print(f"    UYARI: {timeframe} için backtest verisi yok, atlanıyor.")
        return False

    save_pivot_stats(ticker, stats, timeframe=timeframe)
    print(f"    ✓ Backtest kaydedildi ({sum(len(v) for v in stats.values())} seviye)")

    df = resample_to_timeframe(raw_df, timeframe)
    if df.empty or len(df) < 2:
        print(f"    UYARI: {timeframe} için confluence hesaplanamadı (yetersiz veri).")
        return True

    prev_row = df.iloc[-2]
    today_row = df.iloc[-1]

    pivots = calculate_all_pivots(
        prev_open=prev_row["Open"], prev_high=prev_row["High"],
        prev_low=prev_row["Low"], prev_close=prev_row["Close"],
        today_open=today_row["Open"],
    )
    zones = find_confluence_zones(pivots)
    save_confluence_zones(ticker, zones, timeframe=timeframe)
    print(f"    ✓ Confluence kaydedildi ({len(zones)} zone bulundu)")

    return True

def update_all_stocks():
    baslangic = time.time()
    create_tables() 
    basarili = []
    basarisiz = []
    total_combos = len(BIST_STOCKS) * len(TIMEFRAMES)
    combo_index = 0

    for ticker in BIST_STOCKS:
        raw_df = get_stock_data(ticker)

        if raw_df.empty:
            print(f"\n{ticker}: UYARI -veri çekilemedi, tüm zaman dilimleri atlanıyor.")
            for timeframe in TIMEFRAMES:
                combo_index += 1
                basarisiz.append(f"{ticker} ({timeframe})")
            continue

        for timeframe in TIMEFRAMES:
            combo_index += 1
            print(f"\n[{combo_index}/{total_combos}] {ticker} - {timeframe}:")
            try:
                if update_single_stock_timeframe(ticker, timeframe, raw_df):
                    basarili.append(f"{ticker} ({timeframe})")
                else:
                    basarisiz.append(f"{ticker} ({timeframe})")
            except Exception as e:
                print(f"    HATA: {e}")
                basarisiz.append(f"{ticker} ({timeframe})")

    sure_dk = (time.time() - baslangic) / 60

    print(f"\n{'='*50}")
    print("ÖZET")
    print(f"{'='*50}")
    print(f"Başarılı: {len(basarili)}/{total_combos}")
    print(f"Süre: {sure_dk:.1f} dakika")
    if basarisiz:
        print(f"Başarısız ({len(basarisiz)}): {basarisiz}")

    # --- Adminlere Telegram raporu gönder ---
    durum_ikonu = "✅" if not basarisiz else "⚠️"
    rapor = (
        f"{durum_ikonu} Veri Güncelleme Raporu\n\n"
        f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"Başarılı: {len(basarili)}/{total_combos}\n"
        f"Süre: {sure_dk:.1f} dakika"
    )
    if basarisiz:
        ornekler = ", ".join(basarisiz[:10])
        rapor += f"\n\nBaşarısız ({len(basarisiz)}): {ornekler}"
        if len(basarisiz) > 10:
            rapor += f" ... (+{len(basarisiz) - 10} tane daha)"

    admin_ids = get_admin_chat_ids()
    if not admin_ids:
        print("\nUYARI: Telegram bağlı admin kullanıcı bulunamadı, rapor gönderilemedi.")
    else:
        for chat_id in admin_ids:
            if send_telegram_message(chat_id, rapor):
                print(f"\nRapor gönderildi (chat_id: {chat_id})")
            else:
                print(f"\nUYARI: Rapor gönderilemedi (chat_id: {chat_id})")

if __name__ == "__main__":
    update_all_stocks()
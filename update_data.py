from config import BIST_STOCKS, TIMEFRAMES
from data_fetcher import get_stock_data, resample_to_timeframe
from pivot_calculations import calculate_all_pivots
from confluence import find_confluence_zones
from backtester import backtest_stock
from database import create_tables, save_pivot_stats, save_confluence_zones

def update_single_stock_timeframe(ticker: str, timeframe: str, raw_df) -> bool:
    """Tek bir hisse + tek bir zaman dilimi için backtest + confluence değerini hesaplayıp kaydeder."""
    stats = backtest_stock(ticker, timeframe=timeframe, raw_df=raw_df)
    if not stats:
        print(f"    UYARI: {timeframe} için backtest verisi yok, atlanıyor.")
        return False

    save_pivot_stats(ticker, stats, timeframe=timeframe)
    print(f"    ✓ Backtest kaydedildi ({sum(len(v) for v in stats.values())} seviye)")

    df = resample_to_timeframe(raw_df, timeframe)
    if df.empty or len(df) < 2:
        print(f"    UYARI: {timeframe} için confluence hesaplanamadı (yetersiz veri).")
        return True  # backtest zaten kaydedildi, kısmi başarı sayılır

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
    """BIST_STOCKS listesindeki tüm hisseleri, TIMEFRAMES'teki tüm zaman dilimlerinde günceller."""
    create_tables()  # tablolar yoksa oluşturur, migration da otomatik çalışır

    basarili = []
    basarisiz = []
    total_combos = len(BIST_STOCKS) * len(TIMEFRAMES)
    combo_index = 0

    for ticker in BIST_STOCKS:
        raw_df = get_stock_data(ticker)  

        if raw_df.empty:
            print(f"\n{ticker}: UYARI - veri çekilemedi, tüm zaman dilimleri atlanıyor.")
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

    print(f"\n{'='*50}")
    print("ÖZET")
    print(f"{'='*50}")
    print(f"Başarılı: {len(basarili)}/{total_combos}")
    if basarisiz:
        print(f"Başarısız ({len(basarisiz)}): {basarisiz}")

if __name__ == "__main__":
    update_all_stocks()
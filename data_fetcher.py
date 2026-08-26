import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

from config import BACKTEST_YEARS

def get_stock_data(ticker: str, years: int = BACKTEST_YEARS) -> pd.DataFrame:
    """Spesifik bir hisse için veri çekilir."""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=years * 365)

    try:
        df = yf.download(
            ticker,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            progress=False,
        )

        if df.empty:
            print(f"UYARI: {ticker} için veri bulunamadı.")
            return pd.DataFrame()

        # yfinance bazen multi-index sütun döndürmekte, tek hisse çekilmek istendiğinden düzleştiriyorum.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df

    except Exception as e:
        print(f"HATA: {ticker} verisi çekilirken sorun oluştu: {e}")
        return pd.DataFrame()

def get_multiple_stocks_data(tickers: list) -> dict:
    """Birden fazla hisse için veri çekilir."""
    result = {}
    for ticker in tickers:
        print(f"{ticker} verisi çekiliyor...")
        result[ticker] = get_stock_data(ticker)
    return result

def resample_to_timeframe(df: pd.DataFrame, timeframe: str = "daily") -> pd.DataFrame:
    """Günlük OHLC verisini haftalık veya aylık zaman dilimine dönüştürür.
    Not: Volume sütunu pivot hesaplamalarında hiç kullanılmıyor, ama varsa doğru şekilde toplanır(sum). 
    Sütun yoksa (örn. testlerde kullanılan basit sahte veri) hata fırlatmadan devam edilir -bu,
    fonksiyonu hem gerçek yfinance verisiyle hem de Volume içermeyen minimal test verileriyle uyumlu hale getirir."""
    if timeframe == "daily":
        return df

    if timeframe == "weekly":
        rule = "W"
    elif timeframe == "monthly":
        rule = "ME"  # "Month End" - pandas 2.2+ önerilen kısaltma
    else:
        raise ValueError(f"Bilinmeyen timeframe: {timeframe}. 'daily', 'weekly' veya 'monthly' olmalı.")

    agg_rules = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    if "Volume" in df.columns:
        agg_rules["Volume"] = "sum"

    resampled = df.resample(rule).agg(agg_rules)

    # Hiç işlem olmayan dönemler NaN satır üretebilir, temizle.
    resampled = resampled.dropna()

    return resampled

if __name__ == "__main__":
    from config import BIST_STOCKS
    # Sadece ilk hisseyle ilgili hızlı bir test
    test_ticker = BIST_STOCKS[0]
    data = get_stock_data(test_ticker)
    print(f"\n{test_ticker} için son 5 gün:")
    print(data.tail())
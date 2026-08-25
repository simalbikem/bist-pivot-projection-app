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

if __name__ == "__main__":
    from config import BIST_STOCKS
    # Sadece ilk hisseyle ilgili hızlı bir test.
    test_ticker = BIST_STOCKS[0]
    data = get_stock_data(test_ticker)
    print(f"\n{test_ticker} için son 5 gün:")
    print(data.tail())
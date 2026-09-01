from data_fetcher import get_stock_data
from pivot_calculations import calculate_all_pivots
import yfinance as yf

for ticker in ["THYAO.IS", "AEFES.IS", "AKBNK.IS"]:
    raw_df = get_stock_data(ticker)
    prev_row = raw_df.iloc[-1]
    fi = yf.Ticker(ticker).fast_info

    pivots = calculate_all_pivots(
        prev_open=prev_row["Open"], prev_high=prev_row["High"],
        prev_low=prev_row["Low"], prev_close=prev_row["Close"],
        today_open=fi["open"],
    )

    day_low = fi["dayLow"]
    day_high = fi["dayHigh"]

    print(f"--- {ticker} (Low={day_low:.2f}, High={day_high:.2f}) ---")
    for method, levels in pivots.items():
        for level_name, value in levels.items():
            if day_low <= value <= day_high:
                print(f"  TOUCH ARALIGINDA: {method} {level_name} = {value:.2f}")
    print()
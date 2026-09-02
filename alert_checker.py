"""
Tüm aktif alertleri kontrol eder, koşulu sağlananlar için Telegram bildirimi gönderir. 
Windows Task Scheduler ile piyasa açıkken periyodik çalıştırılmak üzere tasarlanmıştır.

DAVRANIŞ:
    - "daily" timeframeli alert'ler: yfinance'in fast_info özelliğiyle GERÇEK CANLI fiyatı kullanır.
      "break" kontrolü, henüz kesinleşmemiş güncel fiyata dayanır 
      -piyasa kapanana kadar bu durum değişebilir, bu bir "provizyonel" sinyaldir.
    - "weekly"/"monthly" alertler: canlı veri kullanılmaz, bunun yerine günlük geçmiş veri 
      resample edilerek şu ana kadar tamamlanmış günlerden oluşan  bu haftanın/ayın kısmi barı" kullanılır. 
      Bu, haftalık/aylık alertlerin gün içi hassasiyet gerektirmediği varsayımına dayanan bilinçli bir basitleştirmedir.
    - Aynı alert, aynı gün içinde SADECE BİR KEZ tetiklenir.
"""
import yfinance as yf
from datetime import date
from datetime import datetime
from data_fetcher import get_stock_data, resample_to_timeframe
from pivot_calculations import calculate_all_pivots
from backtester import check_touch, check_directional_break, check_pp_break, determine_level_type
from database import get_all_active_alerts_with_contact, mark_alert_triggered
from notifications import send_telegram_message

def get_level_and_today_ohlc(ticker: str, timeframe: str, raw_df, fast_info_cache: dict):
    """Belirtilen ticker/timeframe için (prev OHLCden hesaplanan) pivot seviyelerini 
    ve "bugünün/bu dönemin" karşılaştırılacak OHLC'sini döner."""
    if timeframe == "daily":
        if ticker not in fast_info_cache:
            try:
                fast_info_cache[ticker] = yf.Ticker(ticker).fast_info
            except Exception as e:
                print(f"    WARNING: {ticker}'s live data could not be retrieved for: {e}")
                fast_info_cache[ticker] = None

        fi = fast_info_cache[ticker]
        if fi is None or raw_df.empty:
            return None, None

        prev_row = raw_df.iloc[-1]  # son TAMAMLANMIŞ gün(dün)
        today_ohlc = {
            "Open": fi["open"], "High": fi["dayHigh"],
            "Low": fi["dayLow"], "Close": fi["lastPrice"],
        }
    else:
        df_tf = resample_to_timeframe(raw_df, timeframe)
        if len(df_tf) < 2:
            return None, None
        prev_row = df_tf.iloc[-2]
        today_row = df_tf.iloc[-1]
        today_ohlc = {
            "Open": today_row["Open"], "High": today_row["High"],
            "Low": today_row["Low"], "Close": today_row["Close"],
        }

    pivots = calculate_all_pivots(
        prev_open=prev_row["Open"], prev_high=prev_row["High"],
        prev_low=prev_row["Low"], prev_close=prev_row["Close"],
        today_open=today_ohlc["Open"],
    )
    return pivots, today_ohlc

def check_alert_condition(alert, pivots: dict, today_ohlc: dict) -> tuple[bool, float | None]:
    """Bir alertin koşulunun sağlanıp sağlanmadığını kontrol eder."""
    level_value = pivots.get(alert["method"], {}).get(alert["level_name"])
    if level_value is None:
        return False, None 

    if alert["condition_type"] == "touch":
        triggered = check_touch(today_ohlc["High"], today_ohlc["Low"], level_value)
    else:  # break
        level_type = determine_level_type(alert["level_name"])
        if level_type == "pp":
            break_up, break_down = check_pp_break(today_ohlc["Close"], level_value)
            triggered = break_up or break_down
        else:
            triggered = check_directional_break(today_ohlc["Close"], level_value, level_type)

    return triggered, level_value

def run_alert_checks():
    """Tüm aktif alertleri kontrol edip gerekli Telegram bildirimlerini gönderir."""
    with open("alert_checker.log", "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now()}] alert_checker.py ran.\n")
    
    today_str = date.today().isoformat()

    alerts_df = get_all_active_alerts_with_contact()
    if alerts_df.empty:
        print("There are no active alerts to check.")
        return

    print(f"{len(alerts_df)} active alerts are being checked...")

    fast_info_cache = {}
    pivots_cache = {}  # (ticker, timeframe) -> (pivots, today_ohlc)
    gonderilen = 0

    for ticker in alerts_df["ticker"].unique():
        ticker_alerts = alerts_df[alerts_df["ticker"] == ticker]

        raw_df = get_stock_data(ticker)
        if raw_df.empty:
            print(f"  WARNING: No data available for {ticker}, skipping.")
            continue

        for _, alert in ticker_alerts.iterrows():
            timeframe = alert["timeframe"]
            cache_key = (ticker, timeframe)

            if cache_key not in pivots_cache:
                pivots, today_ohlc = get_level_and_today_ohlc(ticker, timeframe, raw_df, fast_info_cache)
                pivots_cache[cache_key] = (pivots, today_ohlc)

            pivots, today_ohlc = pivots_cache[cache_key]
            if pivots is None:
                continue

            triggered, level_value = check_alert_condition(alert, pivots, today_ohlc)
            already_sent_today = alert["last_triggered_date"] == today_str

            if triggered and not already_sent_today:
                message = (
                    f"🔔 {alert['ticker']} - {alert['method'].capitalize()} {alert['level_name']} "
                    f"seviyesine {alert['condition_type'].upper()} gerçekleşti!\n"
                    f"Seviye: {level_value:.2f} | Güncel fiyat: {today_ohlc['Close']:.2f}\n"
                    f"Zaman Aralığı: {timeframe.capitalize()}"
                )
                sent = send_telegram_message(alert["telegram_chat_id"], message)
                if sent:
                    mark_alert_triggered(int(alert["id"]), today_str)
                    gonderilen += 1
                    print(f"  ✓ Notification sent: {alert['username']} - {ticker} {alert['level_name']}")
                else:
                    print(f"  ✗ Failed to send notification: {alert['username']} - {ticker} {alert['level_name']}")

    print(f"\nTotal {gonderilen} notifications sent.")
    with open("alert_checker.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] Finished. {gonderilen} notifications sent.\n")

if __name__ == "__main__":
    run_alert_checks()
"""
Geçmiş verilerin, her günü için pivot seviyelerini hesaplar ve bir sonraki günün fiyat hareketinin 
bu seviyelere "dokunup (touch) dokunmadığını" ve "kırıp (break) kırmadığını" kontrol eder. 
Sonunda her yöntem/seviye için touch ve break istatistiklerini üretir.

  - TOUCH (varsayılan mod = "range"):
        Günün Low-High aralığı seviyeyi içeriyorsa (Low <= seviye <= High) "touch" sayılır.
        İkinci bir mod olan "tolerance" da mevcuttur: Low veya High,
        seviyeye TOUCH_THRESHOLD_PCT kadar yakınsa da "touch" sayılır
        (daha gevşek/toleranslı bir alternatif, ihtiyaç halinde kullanılır).

  - BREAK - R/S seviyeleri için (yönlü):
        Günün KAPANIŞI (Close), seviyeyi BREAK_THRESHOLD_PCT kadar geçtiyse "break" sayılır. 
        Sadece High/Low ile geçici bir sapma "break" sayılmaz - piyasa o günü o seviyenin ötesinde KAPATMALI.
        - Resistance (R1, R2, R3): Close, seviyenin ÜSTÜNDE kapandıysa.
        - Support (S1, S2, S3): Close, seviyenin ALTINDA kapandıysa.

  - BREAK - PP için (yönsüz, iki ayrı olasılık):
        PP'nin R/S gibi doğal bir yönü olmadığı için, PP'nin kırılması İKİ AYRI olasılık olarak raporlanır:
        - break_up_probability: Close, PP'nin BREAK_THRESHOLD_PCT kadar ÜSTÜNDE kapandığı gün oranı.
        - break_down_probability: Close, PP'nin BREAK_THRESHOLD_PCT kadar ALTINDA kapandığı gün oranı.
        Bu, "PP genelde hangi yönde kırılıyor" sorusunu cevaplamamızı sağlar.

WOODIE İSTİSNASI:
        Her dönem için pivot hesaplanırken, Woodie yöntemi diğerlerinden farklı olarak BUGÜNÜN/BU DÖNEMİN
        Open değerini kullanır, diğer 4 yöntem ise tamamen ÖNCEKİ dönemin OHLC'sine dayanır. Bu yüzden
        pivot_calculations.calculate_all_pivots() her çağrıldığında hem "prev_*" hem "today_open" ayrı ayrı verilir.

RAW_DF PARAMETRESİ:
        backtest_stock artık isteğe bağlı bir raw_df parametresi kabul
        eder. Bu, update_data.py gibi çağıranların, aynı hissenin ham
        günlük verisini BİR KEZ çekip 3 zaman diliminde (daily/weekly/
        monthly) yeniden kullanmasını sağlar - Yahoo Finance'e gereksiz
        tekrar istek atılmasını önler. raw_df verilmezse (varsayılan
        None), fonksiyon kendisi get_stock_data ile çeker - böylece
        eski kullanım şekli (sadece ticker vererek çağırma) hâlâ çalışır.
"""
import pandas as pd

from config import TOUCH_THRESHOLD_PCT, BREAK_THRESHOLD_PCT
from data_fetcher import get_stock_data, resample_to_timeframe
from pivot_calculations import calculate_all_pivots

def determine_level_type(level_name: str) -> str:
    if level_name.startswith("R"):
        return "resistance"
    elif level_name.startswith("S"):
        return "support"
    else:
        return "pp"

def check_touch(
    day_high: float,
    day_low: float,
    level_value: float,
    mode: str = "range",
    tolerance_pct: float = TOUCH_THRESHOLD_PCT,
) -> bool:
    
    if mode == "range":
        return day_low <= level_value <= day_high
    elif mode == "tolerance":
        dist_high = abs(day_high - level_value) / level_value
        dist_low = abs(day_low - level_value) / level_value
        return min(dist_high, dist_low) <= tolerance_pct
    else:
        raise ValueError(f"Bilinmeyen mode: {mode}. 'range' veya 'tolerance' olmalı.")

def check_directional_break(
    day_close: float,
    level_value: float,
    level_type: str,
    threshold_pct: float = BREAK_THRESHOLD_PCT,
) -> bool:

    if level_type == "resistance":
        return day_close > level_value * (1 + threshold_pct)
    elif level_type == "support":
        return day_close < level_value * (1 - threshold_pct)
    else:
        raise ValueError("check_directional_break sadece 'resistance' veya 'support' için kullanılır.")

def check_pp_break(
    day_close: float,
    pp_value: float,
    threshold_pct: float = BREAK_THRESHOLD_PCT,
) -> tuple[bool, bool]:

    break_up = day_close > pp_value * (1 + threshold_pct)
    break_down = day_close < pp_value * (1 - threshold_pct)
    return break_up, break_down

def backtest_stock(
    ticker: str,
    touch_mode: str = "range",
    timeframe: str = "daily",
    raw_df: pd.DataFrame = None,
) -> dict:

    if raw_df is None:
        raw_df = get_stock_data(ticker)

    if raw_df.empty:
        print(f"UYARI: {ticker} için veri yok, backtest atlanıyor.")
        return {}

    df = resample_to_timeframe(raw_df, timeframe)

    if df.empty or len(df) < 3:
        print(f"UYARI: {ticker} için {timeframe} bazında yeterli veri yok, backtest atlanıyor.")
        return {}

    # Ham sayaçları biriktirileceği yapı
    stats = {}

    for i in range(1, len(df)):
        prev_row = df.iloc[i - 1]
        today_row = df.iloc[i]

        pivots = calculate_all_pivots(
            prev_open=prev_row["Open"],
            prev_high=prev_row["High"],
            prev_low=prev_row["Low"],
            prev_close=prev_row["Close"],
            today_open=today_row["Open"],  # Woodie için kritik
        )

        for method, levels in pivots.items():
            stats.setdefault(method, {})

            for level_name, level_value in levels.items():
                stats[method].setdefault(level_name, {
                    "touches": 0,
                    "breaks": 0,           # sadece R/S için kullanılır.
                    "breaks_up": 0,        # sadece PP için kullanılır.
                    "breaks_down": 0,      # sadece PP için kullanılır.
                    "total_days": 0,
                })
                s = stats[method][level_name]
                s["total_days"] += 1

                # --- Touch kontrolü (tüm seviye tipleri için ortak) ---
                if check_touch(today_row["High"], today_row["Low"], level_value, mode=touch_mode):
                    s["touches"] += 1

                # --- Break kontrolü (tipe göre dallanıyor) ---
                level_type = determine_level_type(level_name)

                if level_type in ("resistance", "support"):
                    if check_directional_break(today_row["Close"], level_value, level_type):
                        s["breaks"] += 1
                else:  # "pp"
                    break_up, break_down = check_pp_break(today_row["Close"], level_value)
                    if break_up:
                        s["breaks_up"] += 1
                    if break_down:
                        s["breaks_down"] += 1

    # Ham sayaçlardan olasılıkları hesaplanır.
    results = {}
    for method, levels in stats.items():
        results[method] = {}
        for level_name, s in levels.items():
            total = s["total_days"]
            level_type = determine_level_type(level_name)

            touch_prob = s["touches"] / total if total > 0 else 0.0

            if level_type in ("resistance", "support"):
                break_prob = s["breaks"] / total if total > 0 else None
                break_up_prob = None
                break_down_prob = None
            else:  # "pp"
                break_prob = None
                break_up_prob = s["breaks_up"] / total if total > 0 else None
                break_down_prob = s["breaks_down"] / total if total > 0 else None

            results[method][level_name] = {
                "touch_probability": round(touch_prob, 4),
                "break_probability": round(break_prob, 4) if break_prob is not None else None,
                "break_up_probability": round(break_up_prob, 4) if break_up_prob is not None else None,
                "break_down_probability": round(break_down_prob, 4) if break_down_prob is not None else None,
                "sample_size": total,
            }

    return results

# Hızlı test
if __name__ == "__main__":
    from config import BIST_STOCKS

    test_ticker = BIST_STOCKS[0]

    for tf in ["daily", "weekly", "monthly"]:
        print(f"\n{'='*50}")
        print(f"{test_ticker} için {tf} backtest çalışıyor...")
        print(f"{'='*50}")

        sonuclar = backtest_stock(test_ticker, timeframe=tf)

        if not sonuclar:
            continue

        pp_stat = sonuclar["classic"]["PP"]
        print(f"  classic/PP: touch={pp_stat['touch_probability']*100:.1f}%  "
              f"break_up={pp_stat['break_up_probability']*100:.1f}%  "
              f"break_down={pp_stat['break_down_probability']*100:.1f}%  "
              f"(n={pp_stat['sample_size']})")
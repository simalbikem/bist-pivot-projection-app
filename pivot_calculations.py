"""
pivot-points calculator: Classic, Fibonacci, Camarilla, DeMark, Woodie.
Formül kaynakları doğrulanmıştır (Tradingpedia, Babypips, Overcharts - Ağustos 2026).
"""
import pandas as pd

def classic_pivot(high: float, low: float, close: float) -> dict:
    pp = (high + low + close) / 3
    r1 = (2 * pp) - low
    s1 = (2 * pp) - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)

    return {
        "PP": pp,
        "R1": r1, "R2": r2, "R3": r3,
        "S1": s1, "S2": s2, "S3": s3,
    }

def fibonacci_pivot(high: float, low: float, close: float) -> dict:
    pp = (high + low + close) / 3
    diff = high - low

    r1 = pp + 0.382 * diff
    r2 = pp + 0.618 * diff
    r3 = pp + 1.000 * diff
    s1 = pp - 0.382 * diff
    s2 = pp - 0.618 * diff
    s3 = pp - 1.000 * diff

    return {
        "PP": pp,
        "R1": r1, "R2": r2, "R3": r3,
        "S1": s1, "S2": s2, "S3": s3,
    }

def camarilla_pivot(high: float, low: float, close: float) -> dict:
    diff = high - low

    r1 = close + diff * 1.1 / 12
    r2 = close + diff * 1.1 / 6
    r3 = close + diff * 1.1 / 4
    s1 = close - diff * 1.1 / 12
    s2 = close - diff * 1.1 / 6
    s3 = close - diff * 1.1 / 4

    return {
        "PP": close,
        "R1": r1, "R2": r2, "R3": r3,
        "S1": s1, "S2": s2, "S3": s3,
    }

def demark_pivot(open_: float, high: float, low: float, close: float) -> dict:
    if close < open_:
        x = high + (2 * low) + close
    elif close > open_:
        x = (2 * high) + low + close
    else:  # close == open_
        x = high + low + (2 * close)

    pp = x / 4
    r1 = (x / 2) - low
    s1 = (x / 2) - high

    return {
        "PP": pp,
        "R1": r1,
        "S1": s1,
    }

def woodie_pivot(open_: float, high: float, low: float, close: float) -> dict:
    pp = (high + low + 2 * open_) / 4
    r1 = (2 * pp) - low
    s1 = (2 * pp) - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)

    return {
        "PP": pp,
        "R1": r1, "R2": r2, "R3": r3,
        "S1": s1, "S2": s2, "S3": s3,
    }

def calculate_all_pivots(
    prev_open: float,
    prev_high: float,
    prev_low: float,
    prev_close: float,
    today_open: float = None,
) -> dict:
    
    o, h, l, c = prev_open, prev_high, prev_low, prev_close

    # Woodie için bugünün open'ı verilmediyse, önceki günün open'ını kullanılmaktadır (yaklaşık sonuç - backtester.py'de gerçek değer verilecektir).
    woodie_open = today_open if today_open is not None else prev_open

    return {
        "classic": classic_pivot(h, l, c),
        "fibonacci": fibonacci_pivot(h, l, c),
        "camarilla": camarilla_pivot(h, l, c),
        "demark": demark_pivot(o, h, l, c),
        "woodie": woodie_pivot(woodie_open, h, l, c),
    }

# Hızlı test
if __name__ == "__main__":
    # Örnek: önceki günün OHLC'si + bugünün open'ı
    prev_open, prev_high, prev_low, prev_close = 100.0, 105.0, 98.0, 103.0
    today_open = 103.5

    sonuclar = calculate_all_pivots(
        prev_open, prev_high, prev_low, prev_close, today_open
    )

    for yontem, seviyeler in sonuclar.items():
        print(f"\n{yontem.upper()}:")
        for seviye, deger in seviyeler.items():
            print(f"  {seviye}: {deger:.2f}")
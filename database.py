"""
Backtest sonuçlarını (pivot_stats) ve confluence zone verilerini SQLite veritabanına kaydeder ve okur.
"""
import sqlite3
import pandas as pd

from config import DATABASE_PATH

def get_connection() -> sqlite3.Connection:
    """
    Veritabanına bağlantı açar. FOREIGN KEY kısıtlamalarının çalışması için PRAGMA ayarını da burada aktif eder 
    -SQLite'ta bu varsayılan olarak KAPALIDIR, her bağlantıda ayrıca açılması gerekir.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pivot_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            method TEXT NOT NULL,
            level_name TEXT NOT NULL,
            touch_probability REAL,
            break_probability REAL,
            break_up_probability REAL,
            break_down_probability REAL,
            sample_size INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS confluence_zones (
            zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            center REAL NOT NULL,
            method_count INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS confluence_contributors (
            contributor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            level_name TEXT NOT NULL,
            value REAL NOT NULL,
            FOREIGN KEY (zone_id) REFERENCES confluence_zones (zone_id)
        )
    """)

    conn.commit()
    conn.close()
    print("Tablolar hazır.")

def save_pivot_stats(ticker: str, stats: dict):
    """
    Aynı ticker için önceki kayıtları önce silinir, böylece backtest tekrar çalıştırdığında veri çoğalmaz, güncellenir.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM pivot_stats WHERE ticker = ?", (ticker,))

    for method, levels in stats.items():
        for level_name, s in levels.items():
            cursor.execute("""
                INSERT INTO pivot_stats
                    (ticker, method, level_name, touch_probability,
                     break_probability, break_up_probability,
                     break_down_probability, sample_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker, method, level_name,
                s["touch_probability"], s["break_probability"],
                s["break_up_probability"], s["break_down_probability"],
                s["sample_size"],
            ))

    conn.commit()
    conn.close()

def save_confluence_zones(ticker: str, zones: list):
    """
    Aynı ticker için önceki zonelar silinir -ancak önce contributorsın silinmesi gerekir. (foreign key kısıtlaması onları zonesdan önce silinmesini zorunlu kılar).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Önce bu ticker'a ait eski zone_id'leri bulunur, sonra contributors silinir.
    cursor.execute("SELECT zone_id FROM confluence_zones WHERE ticker = ?", (ticker,))
    old_zone_ids = [row[0] for row in cursor.fetchall()]
    for zid in old_zone_ids:
        cursor.execute("DELETE FROM confluence_contributors WHERE zone_id = ?", (zid,))
    cursor.execute("DELETE FROM confluence_zones WHERE ticker = ?", (ticker,))

    for zone in zones:
        cursor.execute("""
            INSERT INTO confluence_zones (ticker, center, method_count)
            VALUES (?, ?, ?)
        """, (ticker, zone["center"], zone["method_count"]))

        new_zone_id = cursor.lastrowid

        for c in zone["contributors"]:
            cursor.execute("""
                INSERT INTO confluence_contributors (zone_id, method, level_name, value)
                VALUES (?, ?, ?, ?)
            """, (new_zone_id, c["method"], c["level"], c["value"]))

    conn.commit()
    conn.close()

def get_pivot_stats(ticker: str) -> pd.DataFrame:
    """
    Bir hissenin tüm pivot_stats satırlarını pandas DataFrame olarak döner.
    """
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM pivot_stats WHERE ticker = ?", conn, params=(ticker,)
    )
    conn.close()
    return df

def get_confluence_zones(ticker: str) -> pd.DataFrame:
    """
    Bir hissenin confluence zone'larını, contributors detayıyla BİRLİKTE döner (JOIN). 
    İki tablo zone_id üzerinden birleştirilir, böylece her satırda hem zone'un özeti 
    (center, method_count) hem de o satıra ait tek bir contributor bilgisi bulunur.
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            z.zone_id,
            z.ticker,
            z.center,
            z.method_count,
            c.method,
            c.level_name,
            c.value
        FROM confluence_zones z
        JOIN confluence_contributors c ON z.zone_id = c.zone_id
        WHERE z.ticker = ?
        ORDER BY z.method_count DESC, z.zone_id
    """, conn, params=(ticker,))
    conn.close()
    return df

# Hızlı test 
if __name__ == "__main__":
    from config import BIST_STOCKS
    from backtester import backtest_stock
    from pivot_calculations import calculate_all_pivots
    from confluence import find_confluence_zones
    from data_fetcher import get_stock_data

    create_tables()

    test_ticker = BIST_STOCKS[0]

    # 1. Backtest sonuçlarını kaydet.
    print(f"{test_ticker} için backtest çalışıyor ve kaydediliyor...")
    stats = backtest_stock(test_ticker)
    save_pivot_stats(test_ticker, stats)

    # 2. Confluence zoneları kaydet. (son güne ait pivotlarla)
    df = get_stock_data(test_ticker)
    prev_row = df.iloc[-2]
    today_row = df.iloc[-1]
    pivots = calculate_all_pivots(
        prev_open=prev_row["Open"], prev_high=prev_row["High"],
        prev_low=prev_row["Low"], prev_close=prev_row["Close"],
        today_open=today_row["Open"],
    )
    zones = find_confluence_zones(pivots)
    save_confluence_zones(test_ticker, zones)

    # 3. Geri okuyup kontrol et.
    print("\n--- pivot_stats'tan okunan ilk 5 satır ---")
    print(get_pivot_stats(test_ticker).head())

    print("\n--- confluence_zones + contributors ---")
    print(get_confluence_zones(test_ticker))
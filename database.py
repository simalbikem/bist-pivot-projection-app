"""
Backtest sonuçlarını (pivot_stats) ve confluence zone verilerini SQLite veritabanına kaydeder ve okur.
"""
import sqlite3
import pandas as pd

from config import DATABASE_PATH

def get_connection() -> sqlite3.Connection:
    """Veritabanına bağlantı açar. FOREIGN KEY kısıtlamalarının çalışması için PRAGMA ayarını da burada aktif eder 
    -SQLite'ta bu varsayılan olarak KAPALIDIR, her bağlantıda ayrıca açılması gerekir."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Bir tabloda belirli bir sütunun var olup olmadığını kontrol eder."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_add_timeframe_column():
    """MIGRATION: pivot_stats ve confluence_zones tablolarına 'timeframe' sütunu ekler(yoksa). 
    Mevcut tüm satırlar otomatik olarak timeframe='daily' değerini alır 
    -bu, o veriler zaten günlük veriyle üretildiği için doğru bir varsayılan."""
    conn = get_connection()
    cursor = conn.cursor()

    for table in ["pivot_stats", "confluence_zones"]:
        if _column_exists(cursor, table, "timeframe"):
            print(f"  {table}: 'timeframe' sütunu zaten var, atlanıyor.")
        else:
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN timeframe TEXT NOT NULL DEFAULT 'daily'"
            )
            print(f"  {table}: 'timeframe' sütunu eklendi (mevcut satırlar 'daily' aldı).")

    conn.commit()
    conn.close()

def migrate_add_updated_at_column():
    conn = get_connection()
    cursor = conn.cursor()

    if _column_exists(cursor, "pivot_stats", "updated_at"):
        print("  pivot_stats: 'updated_at' sütunu zaten var, atlanıyor.")
    else:
        cursor.execute("ALTER TABLE pivot_stats ADD COLUMN updated_at TEXT")
        cursor.execute("UPDATE pivot_stats SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        print("  pivot_stats: 'updated_at' sütunu eklendi (mevcut satırlar şu anki zamanı aldı).")

    conn.commit()
    conn.close()

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pivot_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            method TEXT NOT NULL,
            level_name TEXT NOT NULL,
            timeframe TEXT NOT NULL DEFAULT 'daily',
            touch_probability REAL,
            break_probability REAL,
            break_up_probability REAL,
            break_down_probability REAL,
            sample_size INTEGER,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS confluence_zones (
            zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            timeframe TEXT NOT NULL DEFAULT 'daily',
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

    # Var olan veritabanlarında sütun eksikse otomatik ekler.
    # Yeni oluşturulan veritabanlarında CREATE TABLE zaten sütunu içerdiği için bu fonksiyon onlarda değişiklik yapmaz (idempotent).
    migrate_add_timeframe_column()
    migrate_add_updated_at_column()

def save_pivot_stats(ticker: str, stats: dict, timeframe: str = "daily"):
    """Aynı ticker + timeframe kombinasyonu için önceki kayıtlar önce silinir, 
    böylece backtest tekrar çalıştırdığında veri çoğalmaz, güncellenir. 
    Farklı timeframelerin birbirini silmemesi için WHERE koşuluna timeframe da eklenmiştir."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM pivot_stats WHERE ticker = ? AND timeframe = ?",
        (ticker, timeframe),
    )

    for method, levels in stats.items():
        for level_name, s in levels.items():
            cursor.execute("""
                INSERT INTO pivot_stats
                    (ticker, method, level_name, timeframe, touch_probability,
                     break_probability, break_up_probability,
                     break_down_probability, sample_size, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                ticker, method, level_name, timeframe,
                s["touch_probability"], s["break_probability"],
                s["break_up_probability"], s["break_down_probability"],
                s["sample_size"],
            ))

    conn.commit()
    conn.close()

def save_confluence_zones(ticker: str, zones: list, timeframe: str = "daily"):
    """Aynı ticker + timeframe kombinasyonu için önceki zonelar silinir
    -ancak önce contributors'ın silinmesi gerekir."""
    conn = get_connection()
    cursor = conn.cursor()

    # Önce bu ticker + timeframe'e ait eski zone_idleri bulunur, sonra contributors silinir.
    cursor.execute(
        "SELECT zone_id FROM confluence_zones WHERE ticker = ? AND timeframe = ?",
        (ticker, timeframe),
    )
    old_zone_ids = [row[0] for row in cursor.fetchall()]
    for zid in old_zone_ids:
        cursor.execute("DELETE FROM confluence_contributors WHERE zone_id = ?", (zid,))
    cursor.execute(
        "DELETE FROM confluence_zones WHERE ticker = ? AND timeframe = ?",
        (ticker, timeframe),
    )

    for zone in zones:
        cursor.execute("""
            INSERT INTO confluence_zones (ticker, timeframe, center, method_count)
            VALUES (?, ?, ?, ?)
        """, (ticker, timeframe, zone["center"], zone["method_count"]))

        new_zone_id = cursor.lastrowid

        for c in zone["contributors"]:
            cursor.execute("""
                INSERT INTO confluence_contributors (zone_id, method, level_name, value)
                VALUES (?, ?, ?, ?)
            """, (new_zone_id, c["method"], c["level"], c["value"]))

    conn.commit()
    conn.close()

def get_pivot_stats(ticker: str, timeframe: str = "daily") -> pd.DataFrame:
    """Bir hissenin, belirtilen timeframe'e ait tüm pivot_stats satırlarını pandas DataFrame olarak döner."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM pivot_stats WHERE ticker = ? AND timeframe = ?",
        conn, params=(ticker, timeframe),
    )
    conn.close()
    return df

def get_confluence_zones(ticker: str, timeframe: str = "daily") -> pd.DataFrame:
    """Bir hissenin, belirtilen timeframe'e ait confluence zonelarını, contributors detayıyla JOIN eder. 
    İki tablo zone_id üzerinden birleştirilir, böylece her satırda hem zone'un özeti
    (center, method_count) hem de o satıra ait tek bir contributor bilgisi bulunur."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            z.zone_id,
            z.ticker,
            z.timeframe,
            z.center,
            z.method_count,
            c.method,
            c.level_name,
            c.value
        FROM confluence_zones z
        JOIN confluence_contributors c ON z.zone_id = c.zone_id
        WHERE z.ticker = ? AND z.timeframe = ?
        ORDER BY z.method_count DESC, z.zone_id
    """, conn, params=(ticker, timeframe))
    conn.close()
    return df

def get_last_update_time(ticker: str, timeframe: str = "daily") -> str | None:
    """Belirtilen ticker + timeframe kombinasyonu için pivot_stats
    tablosundaki en son güncelleme zamanını döner."""
    conn = get_connection()
    result = conn.execute(
        "SELECT MAX(updated_at) FROM pivot_stats WHERE ticker = ? AND timeframe = ?",
        (ticker, timeframe),
    ).fetchone()
    conn.close()
    return result[0] if result and result[0] is not None else None

# Hızlı test 
if __name__ == "__main__":
    from config import BIST_STOCKS
    from backtester import backtest_stock
    from pivot_calculations import calculate_all_pivots
    from confluence import find_confluence_zones
    from data_fetcher import get_stock_data

    create_tables()

    test_ticker = BIST_STOCKS[0]

    # 1. Backtest sonuçlarını kayıt eder.
    print(f"{test_ticker} için backtest çalışıyor ve kaydediliyor...")
    stats = backtest_stock(test_ticker)
    save_pivot_stats(test_ticker, stats)

    # 2. Confluence zoneları kayıt eder. (son güne ait pivotlarla)
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

    # 3. Geri okuyup kontrol eder.
    print("\n--- pivot_stats'tan okunan ilk 5 satır ---")
    print(get_pivot_stats(test_ticker).head())

    print("\n--- confluence_zones + contributors ---")
    print(get_confluence_zones(test_ticker))
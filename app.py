import streamlit as st
import pandas as pd

from config import BIST_STOCKS, PIVOT_METHODS
from data_fetcher import get_stock_data
from pivot_calculations import calculate_all_pivots
from database import get_pivot_stats, get_confluence_zones
from charts import plot_candlestick_with_pivots, plot_confluence_zones

st.set_page_config(page_title="BIST Pivot Projection System", layout="wide")

@st.cache_data(ttl=3600)
def cached_get_stock_data(ticker: str) -> pd.DataFrame:
    """get_stock_data 1 saat boyunca önbelleğe alınır -kullanıcı sidebar'da
    farklı seçimler yaptıkça Yahoo Finance'e tekrar tekrar istek atılmasını önler."""
    return get_stock_data(ticker)

def reconstruct_zones_from_db(df_zones: pd.DataFrame) -> list:
    zones = []
    for zone_id, group in df_zones.groupby("zone_id"):
        zones.append({
            "center": group["center"].iloc[0],
            "method_count": group["method_count"].iloc[0],
            "contributors": [
                {"method": row["method"], "level": row["level_name"], "value": row["value"]}
                for _, row in group.iterrows()
            ],
        })
    zones.sort(key=lambda z: z["method_count"], reverse=True)
    return zones

# ---------------------------------------------------------
# Sidebar - kullanıcı girdileri
# ---------------------------------------------------------
st.sidebar.title("Settings")
ticker = st.sidebar.selectbox("Select Stock", BIST_STOCKS)
method = st.sidebar.selectbox("The Pivot Method", PIVOT_METHODS, format_func=str.capitalize)
days_to_show = st.sidebar.slider("Days to Show in Chart", 7, 180, 365)

# ---------------------------------------------------------
# Başlık - yasal uyarı
# ---------------------------------------------------------
st.title("📊BIST Pivot Point Based Stock Projection System")

st.warning(
    "⚠️ This system doesn't provide investment advice."
    "Pivot levels are statistically calculated potential support/resistance zones; we don't guarantee specific price levels."
)

# ---------------------------------------------------------
# Veriyi çek, güncel pivotları hesapla
# ---------------------------------------------------------
df = cached_get_stock_data(ticker)

if df.empty or len(df) < 2:
    st.error(f"{ticker}'s data was not found. Please select another stock.")
    st.stop()

prev_row = df.iloc[-2]
today_row = df.iloc[-1]
pivots = calculate_all_pivots(
    prev_open=prev_row["Open"], prev_high=prev_row["High"],
    prev_low=prev_row["Low"], prev_close=prev_row["Close"],
    today_open=today_row["Open"],
)

# ---------------------------------------------------------
# Sekmeler
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📈Pivot Graph", "🎯 Confluence Zones", "📊 Backtest Statistics"])

with tab1:
    st.subheader(f"{ticker} - {method.capitalize()} Pivot Levels")
    fig = plot_candlestick_with_pivots(df, pivots, ticker, method=method, days_to_show=days_to_show)
    st.plotly_chart(fig, use_container_width=True)

    st.caption("Current Pivot Values (calculated based on today's open)")
    level_df = pd.DataFrame([
        {"Level": k, "Value": round(v, 2)} for k, v in pivots[method].items()
    ])
    st.dataframe(level_df, hide_index=True, use_container_width=True)

with tab2:
    st.subheader(f"{ticker} - Confluence Zones")
    df_zones_db = get_confluence_zones(ticker)

    if df_zones_db.empty:
        st.info(
            "No confluence data available for this stock. "
        )
    else:
        zones = reconstruct_zones_from_db(df_zones_db)
        fig2 = plot_confluence_zones(df, zones, ticker, days_to_show=days_to_show)
        st.plotly_chart(fig2, use_container_width=True)

        st.caption(f"{len(zones)} confluence zone found (ordered from strong to weak)")
        for i, zone in enumerate(zones, start=1):
            methods = ", ".join(sorted({c["method"] for c in zone["contributors"]}))
            with st.expander(f"Zone {i}: {zone['center']:.2f} — {zone['method_count']} methods"):
                st.write(f"**Contributing Methods:** {methods}")
                contrib_df = pd.DataFrame(zone["contributors"])
                st.dataframe(contrib_df, hide_index=True, use_container_width=True)

with tab3:
    st.subheader(f"{ticker} - Backtest Statistics (Touch / Break Probabilities)")
    stats_df = get_pivot_stats(ticker)

    if stats_df.empty:
        st.info(
            "No backtest data available for this stock. "
        )
    else:
        method_stats = stats_df[stats_df["method"] == method].copy()

        for col in ["touch_probability", "break_probability", "break_up_probability", "break_down_probability"]:
            method_stats[col] = (method_stats[col] * 100).round(1)

        display_cols = [
            "level_name", "touch_probability", "break_probability",
            "break_up_probability", "break_down_probability", "sample_size",
        ]
        st.dataframe(
            method_stats[display_cols].rename(columns={
                "level_name": "Level",
                "touch_probability": "Touch %",
                "break_probability": "Break %",
                "break_up_probability": "Break Up %",
                "break_down_probability": "Break Down %",
                "sample_size": "Sample Size",
            }),
            hide_index=True,
            use_container_width=True,
        )
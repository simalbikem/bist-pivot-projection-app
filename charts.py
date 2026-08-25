"""
Plotly kullanarak candlestick graph üretir ve üzerine pivot seviyelerini veya confluence zonelar ekler.
"""
import plotly.graph_objects as go
import pandas as pd

METHOD_COLORS = {
    "classic": "#1f77b4",     
    "fibonacci": "#ff7f0e",   
    "camarilla": "#2ca02c",   
    "demark": "#d62728",      
    "woodie": "#9467bd",      
}

def plot_candlestick_with_pivots(
    df: pd.DataFrame,
    pivots: dict,
    ticker: str,
    method: str = "classic",
    days_to_show: int = 60,
) -> go.Figure:
    """ Belirtilen tek bir yöntemin pivot seviyelerini mum grafiği üzerine çizer.
    Döndürür:
        plotly.graph_objects.Figure"""
    recent_df = df.tail(days_to_show)

    fig = go.Figure()

    # Mum grafiği
    fig.add_trace(go.Candlestick(
        x=recent_df.index,
        open=recent_df["Open"],
        high=recent_df["High"],
        low=recent_df["Low"],
        close=recent_df["Close"],
        name="Fiyat",
    ))

    # Seçilen yöntemin seviyelerini yatay çizgi olarak ekler
    method_levels = pivots.get(method, {})
    color = METHOD_COLORS.get(method, "#7f7f7f")

    for level_name, value in method_levels.items():
        fig.add_hline(
            y=value,
            line_dash="dot",
            line_color=color,
            annotation_text=f"{level_name}: {value:.2f}",
            annotation_position="right",
        )

    fig.update_layout(
        title=f"{ticker} - {method.capitalize()} Pivot Seviyeleri",
        xaxis_title="Tarih",
        yaxis_title="Fiyat",
        xaxis_rangeslider_visible=False,  # alt kaydırma çubuğunu kapat, sade görünüm
        height=600,
    )

    return fig

def plot_confluence_zones(
    df: pd.DataFrame,
    zones: list,
    ticker: str,
    days_to_show: int = 60,
) -> go.Figure:
    """Confluence zone'ları mum grafiği üzerine gölgeli yatay bantlar olarak çizer. 
    Bant kalınlığı, zone içindeki en düşük ve en yüksek katkı değeri arasındaki farktır. 
    Daha çok yöntemin katkı verdiği zonelar daha koyu renkle gösterilir (görsel önem vurgusu)."""
    recent_df = df.tail(days_to_show)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=recent_df.index,
        open=recent_df["Open"],
        high=recent_df["High"],
        low=recent_df["Low"],
        close=recent_df["Close"],
        name="Fiyat",
    ))

    if zones:
        max_methods = max(z["method_count"] for z in zones)
    else:
        max_methods = 1

    for zone in zones:
        values = [c["value"] for c in zone["contributors"]]
        y0, y1 = min(values), max(values)

        # Daha fazla yöntem içeren zone -> daha yüksek opaklık
        opacity = 0.15 + 0.35 * (zone["method_count"] / max_methods)

        methods_str = ", ".join(sorted({c["method"] for c in zone["contributors"]}))

        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor="orange",
            opacity=opacity,
            line_width=0,
            annotation_text=f"{zone['method_count']} yöntem: {methods_str}",
            annotation_position="top left",
        )

    fig.update_layout(
        title=f"{ticker} - Confluence Zone'lar",
        xaxis_title="Tarih",
        yaxis_title="Fiyat",
        xaxis_rangeslider_visible=False,
        height=600,
    )

    return fig

# Hızlı görsel test 
if __name__ == "__main__":
    from config import BIST_STOCKS
    from data_fetcher import get_stock_data
    from pivot_calculations import calculate_all_pivots
    from confluence import find_confluence_zones

    test_ticker = BIST_STOCKS[0]
    df = get_stock_data(test_ticker)

    prev_row = df.iloc[-2]
    today_row = df.iloc[-1]
    pivots = calculate_all_pivots(
        prev_open=prev_row["Open"], prev_high=prev_row["High"],
        prev_low=prev_row["Low"], prev_close=prev_row["Close"],
        today_open=today_row["Open"],
    )

    # Grafik 1: Classic pivot seviyeleri
    fig1 = plot_candlestick_with_pivots(df, pivots, test_ticker, method="classic")
    fig1.write_html("test_chart_classic.html")
    print("test_chart_classic.html oluşturuldu.")

    # Grafik 2: Confluence zonelar
    zones = find_confluence_zones(pivots)
    fig2 = plot_confluence_zones(df, zones, test_ticker)
    fig2.write_html("test_chart_confluence.html")
    print("test_chart_confluence.html oluşturuldu.")
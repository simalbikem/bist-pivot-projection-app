import pandas as pd
import pytest

from charts import plot_candlestick_with_pivots, plot_confluence_zones

def _sahte_ohlc_tablosu(gun_sayisi: int = 10) -> pd.DataFrame:
    """Testlerde kullanılacak basit, artan tarihli sahte OHLC verisi."""
    return pd.DataFrame({
        "Open": [100.0 + i for i in range(gun_sayisi)],
        "High": [105.0 + i for i in range(gun_sayisi)],
        "Low": [95.0 + i for i in range(gun_sayisi)],
        "Close": [102.0 + i for i in range(gun_sayisi)],
    }, index=pd.date_range("2026-01-01", periods=gun_sayisi))

def _sahte_pivots() -> dict:
    """Testlerde kullanılacak, elle belirlenmiş pivot değerleri."""
    return {
        "classic": {"PP": 100.0, "R1": 105.0, "S1": 95.0},
        "fibonacci": {"PP": 100.5, "R1": 106.0, "S1": 94.5},
    }

# ---------------------------------------------------------
# plot_candlestick_with_pivots testleri
# ---------------------------------------------------------
def test_plot_candlestick_includes_candlestick_trace():
    """Grafiğin mutlaka bir Candlestick katmanı içerdiğini doğrular."""
    df = _sahte_ohlc_tablosu()
    pivots = _sahte_pivots()

    fig = plot_candlestick_with_pivots(df, pivots, "TEST.IS", method="classic")

    assert len(fig.data) == 1
    assert fig.data[0].type == "candlestick"

def test_plot_candlestick_draws_correct_number_of_levels():
    """Seçilen yöntemin seviye sayısı kadar yatay çizgi (shape)
    eklendiğini doğrular."""
    df = _sahte_ohlc_tablosu()
    pivots = _sahte_pivots()

    fig = plot_candlestick_with_pivots(df, pivots, "TEST.IS", method="classic")

    assert len(fig.layout.shapes) == 3

def test_plot_candlestick_uses_correct_method_levels():
    """Grafiğin, İSTENEN yöntemin seviyelerini çizdiğini, diğer yöntemin seviyelerini KARIŞTIRMADIĞINI doğrular."""
    df = _sahte_ohlc_tablosu()
    pivots = _sahte_pivots()

    fig = plot_candlestick_with_pivots(df, pivots, "TEST.IS", method="fibonacci")

    y_values = sorted(shape.y0 for shape in fig.layout.shapes)
    expected = sorted(pivots["fibonacci"].values())

    assert y_values == pytest.approx(expected)

def test_plot_candlestick_annotation_text_shows_correct_values():
    """Her seviyenin etiket metninin (annotation), o seviyenin doğruismini ve değerini içerdiğini doğrular."""
    df = _sahte_ohlc_tablosu()
    pivots = {"classic": {"PP": 100.0}}

    fig = plot_candlestick_with_pivots(df, pivots, "TEST.IS", method="classic")

    annotation_texts = [a.text for a in fig.layout.annotations]
    assert any("PP" in text and "100.00" in text for text in annotation_texts)

def test_plot_candlestick_respects_days_to_show():
    df = _sahte_ohlc_tablosu(gun_sayisi=20)
    pivots = _sahte_pivots()

    fig = plot_candlestick_with_pivots(df, pivots, "TEST.IS", method="classic", days_to_show=5)

    assert len(fig.data[0].x) == 5

def test_plot_candlestick_handles_missing_method_gracefully():
    """pivots sözlüğünde olmayan bir yöntem istenirse, hata fırlatmadan boş seviyeli bir grafik döndürdüğünü doğrular."""
    df = _sahte_ohlc_tablosu()
    pivots = _sahte_pivots()

    fig = plot_candlestick_with_pivots(df, pivots, "TEST.IS", method="olmayan_yontem")

    assert len(fig.layout.shapes) == 0

# ---------------------------------------------------------
# plot_confluence_zones testleri
# ---------------------------------------------------------
def test_plot_confluence_zones_includes_candlestick_and_hover_traces():
    df = _sahte_ohlc_tablosu()
    zones = [
        {"center": 100.0, "method_count": 2, "contributors": [
            {"method": "classic", "level": "PP", "value": 100.0},
            {"method": "fibonacci", "level": "PP", "value": 100.2},
        ]},
        {"center": 150.0, "method_count": 3, "contributors": [
            {"method": "classic", "level": "R1", "value": 150.0},
            {"method": "fibonacci", "level": "R1", "value": 150.1},
            {"method": "woodie", "level": "R1", "value": 150.2},
        ]},
    ]

    fig = plot_confluence_zones(df, zones, "TEST.IS")

    assert len(fig.data) == 1 + len(zones)  # 1 candlestick + 2 hover çizgisi
    assert fig.data[0].type == "candlestick"

def test_plot_confluence_zones_draws_correct_number_of_bands():
    """Her zone için tam olarak 1 bant (hrect->shape) çizildiğini doğrular."""
    df = _sahte_ohlc_tablosu()
    zones = [
        {"center": 100.0, "method_count": 2, "contributors": [
            {"method": "classic", "level": "PP", "value": 100.0},
            {"method": "fibonacci", "level": "PP", "value": 100.2},
        ]},
    ]

    fig = plot_confluence_zones(df, zones, "TEST.IS")

    assert len(fig.layout.shapes) == 1

def test_plot_confluence_zones_hover_text_is_capitalized():
    df = _sahte_ohlc_tablosu()
    zones = [
        {"center": 100.0, "method_count": 2, "contributors": [
            {"method": "classic", "level": "PP", "value": 100.0},
            {"method": "camarilla", "level": "PP", "value": 100.1},
        ]},
    ]

    fig = plot_confluence_zones(df, zones, "TEST.IS")

    hover_text = fig.data[1].hovertext  # data[0] candlestick, data[1] ilk zone'un hover'ı
    assert "Classic" in hover_text
    assert "Camarilla" in hover_text
    # Küçük harfli hallerinin metinde GEÇMEDİĞİNİ doğrula (yanlışlıkla
    # eski koda dönülürse bu test kırılır)
    assert "classic," not in hover_text and not hover_text.startswith("classic")

def test_plot_confluence_zones_with_empty_list_still_returns_valid_figure():
    """Boş zone listesi verildiğinde (hiç confluence bulunamadığında), hata fırlatmadan sadece mum grafiğini içeren bir figure döndürüldüğünü doğrular."""
    df = _sahte_ohlc_tablosu()

    fig = plot_confluence_zones(df, [], "TEST.IS")

    assert len(fig.data) == 1  # sadece candlestick, hover çizgisi yok
    assert len(fig.layout.shapes) == 0  # bant yok

def test_plot_confluence_zones_higher_method_count_has_higher_opacity():
    """Daha fazla yöntemden oluşan bir zoneun, daha az yöntemli bir
    zonea göre daha yüksek opaklıkla çizildiğini
    doğrular."""
    df = _sahte_ohlc_tablosu()
    zones = [
        {"center": 100.0, "method_count": 2, "contributors": [
            {"method": "classic", "level": "PP", "value": 100.0},
            {"method": "fibonacci", "level": "PP", "value": 100.1},
        ]},
        {"center": 150.0, "method_count": 5, "contributors": [
            {"method": m, "level": "R1", "value": 150.0 + i}
            for i, m in enumerate(["classic", "fibonacci", "camarilla", "demark", "woodie"])
        ]},
    ]

    fig = plot_confluence_zones(df, zones, "TEST.IS")

    low_opacity = fig.layout.shapes[0].opacity
    high_opacity = fig.layout.shapes[1].opacity

    assert high_opacity > low_opacity
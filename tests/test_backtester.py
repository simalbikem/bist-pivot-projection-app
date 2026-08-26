import pandas as pd
import pytest

import backtester
from backtester import (
    determine_level_type,
    check_touch,
    check_directional_break,
    check_pp_break,
    backtest_stock,
)

# ---------------------------------------------------------
# Saf fonksiyon testleri
# ---------------------------------------------------------
def test_determine_level_type():
    assert determine_level_type("R1") == "resistance"
    assert determine_level_type("R3") == "resistance"
    assert determine_level_type("S1") == "support"
    assert determine_level_type("S3") == "support"
    assert determine_level_type("PP") == "pp"

def test_check_touch_range_mode():
    # Seviye, Low-High aralığının içinde -> True
    assert check_touch(day_high=105, day_low=95, level_value=100, mode="range") is True
    # Seviye, aralığın dışında -> False
    assert check_touch(day_high=105, day_low=95, level_value=110, mode="range") is False

def test_check_touch_tolerance_mode():
    # High'a çok yakın (%0.1 tolerans içinde) -> True
    assert check_touch(day_high=100.05, day_low=90, level_value=100, mode="tolerance", tolerance_pct=0.001) is True
    # Hem High hem Low'dan uzak -> False
    assert check_touch(day_high=110, day_low=95, level_value=100, mode="tolerance", tolerance_pct=0.001) is False

def test_check_touch_invalid_mode_raises_error():
    with pytest.raises(ValueError):
        check_touch(day_high=105, day_low=95, level_value=100, mode="gecersiz_mod")

def test_check_directional_break_resistance():
    # Close, direncin threshold kadar üstünde kapandı -> True
    assert check_directional_break(day_close=110, level_value=100, level_type="resistance", threshold_pct=0.002) is True
    # Close, direncin altında -> False
    assert check_directional_break(day_close=99, level_value=100, level_type="resistance", threshold_pct=0.002) is False

def test_check_directional_break_support():
    # Close, desteğin threshold kadar altında kapandı -> True
    assert check_directional_break(day_close=90, level_value=100, level_type="support", threshold_pct=0.002) is True
    # Close, desteğin üstünde -> False
    assert check_directional_break(day_close=101, level_value=100, level_type="support", threshold_pct=0.002) is False

def test_check_directional_break_invalid_type_raises_error():
    with pytest.raises(ValueError):
        check_directional_break(day_close=100, level_value=100, level_type="pp")

def test_check_pp_break_up():
    break_up, break_down = check_pp_break(day_close=110, pp_value=100, threshold_pct=0.002)
    assert break_up is True
    assert break_down is False

def test_check_pp_break_down():
    break_up, break_down = check_pp_break(day_close=90, pp_value=100, threshold_pct=0.002)
    assert break_up is False
    assert break_down is True

def test_check_pp_break_neither_when_close_to_pp():
    break_up, break_down = check_pp_break(day_close=100, pp_value=100, threshold_pct=0.002)
    assert break_up is False
    assert break_down is False

# ---------------------------------------------------------
# backtest_stock testleri (mock'lu)
# ---------------------------------------------------------
def _elle_hesaplanmis_ohlc_tablosu() -> pd.DataFrame:
    """
    3 günlük elle hesaplanmış sahte veri (sadece Classic yöntemi için, BREAK_THRESHOLD_PCT=0.002 varsayımıyla):

    Gün 0 (referans): Open=100, High=110, Low=90, Close=100
    Gün 1: Open=100, High=105, Low=95, Close=102
    Gün 2: Open=102, High=108, Low=100, Close=106

    --- i=1 (prev=Gün0, today=Gün1) ---
    Classic PP = (110+90+100)/3 = 100.0
    Classic R1 = 2*100-90 = 110.0
    Today High=105, Low=95, Close=102

    Touch(PP=100): 95<=100<=105 -> True
    Touch(R1=110): 110 aralık dışında (105'ten büyük) -> False
    Break_up(PP): Close(102) > 100*1.002=100.2 -> True
    Break(R1, resistance): Close(102) > 110*1.002=110.22 -> False

    --- i=2 (prev=Gün1, today=Gün2) ---
    Classic PP = (105+95+102)/3 = 100.6667
    Classic R1 = 2*100.6667-95 = 106.3333
    Today High=108, Low=100, Close=106

    Touch(PP=100.667): 100<=100.667<=108 -> True
    Touch(R1=106.333): 100<=106.333<=108 -> True
    Break_up(PP): Close(106) > 100.667*1.002=100.868 -> True
    Break(R1, resistance): Close(106) > 106.333*1.002=106.546 -> False

    SONUÇ (Classic, 2 gün üzerinden):
    PP: touch_probability=2/2=1.0, break_up_probability=2/2=1.0, break_down_probability=0.0
    R1: touch_probability=1/2=0.5, break_probability=0/2=0.0
    """
    return pd.DataFrame({
        "Open":  [100.0, 100.0, 102.0],
        "High":  [110.0, 105.0, 108.0],
        "Low":   [90.0, 95.0, 100.0],
        "Close": [100.0, 102.0, 106.0],
    })

def test_backtest_stock_computes_correct_classic_probabilities(monkeypatch):
    """Elle hesaplanmış referans değerlerle backtest_stock'un ürettiği Classic PP ve R1 olasılıkları karşılaştırılır."""
    sahte_veri = _elle_hesaplanmis_ohlc_tablosu()
    monkeypatch.setattr(backtester, "get_stock_data", lambda ticker: sahte_veri)

    # BREAK_THRESHOLD_PCT'in hesaplamalarla aynı (0.002) olduğundan emin olmak için config değeri de aynı şekilde sabitlenir.
    monkeypatch.setattr(backtester, "BREAK_THRESHOLD_PCT", 0.002)

    result = backtest_stock("SAHTE.IS")

    pp_stats = result["classic"]["PP"]
    assert pp_stats["touch_probability"] == pytest.approx(1.0)
    assert pp_stats["break_up_probability"] == pytest.approx(1.0)
    assert pp_stats["break_down_probability"] == pytest.approx(0.0)
    assert pp_stats["break_probability"] is None
    assert pp_stats["sample_size"] == 2

    r1_stats = result["classic"]["R1"]
    assert r1_stats["touch_probability"] == pytest.approx(0.5)
    assert r1_stats["break_probability"] == pytest.approx(0.0)
    assert r1_stats["break_up_probability"] is None
    assert r1_stats["break_down_probability"] is None

def test_backtest_stock_includes_all_five_methods(monkeypatch):
    """backtest_stock'un sonuçlarının 5 yöntemi de kapsadığını doğrular."""
    sahte_veri = _elle_hesaplanmis_ohlc_tablosu()
    monkeypatch.setattr(backtester, "get_stock_data", lambda ticker: sahte_veri)

    result = backtest_stock("SAHTE.IS")

    assert set(result.keys()) == {"classic", "fibonacci", "camarilla", "demark", "woodie"}

def test_backtest_stock_returns_empty_dict_when_data_is_empty(monkeypatch):
    """Veri çekilemezse (boş DataFrame), backtest_stock'un boş dict döndürdüğü doğrulanır."""
    monkeypatch.setattr(backtester, "get_stock_data", lambda ticker: pd.DataFrame())

    result = backtest_stock("GECERSIZ.IS")

    assert result == {}

def test_backtest_stock_returns_empty_dict_when_insufficient_rows(monkeypatch):
    """2'den az satır varsa (bir 'önceki gün' oluşturmaya yetmiyorsa),
    backtest_stock'un boş dict döndürdüğü doğrulanır."""
    yetersiz_veri = pd.DataFrame({
        "Open": [100.0], "High": [105.0], "Low": [95.0], "Close": [102.0],
    })
    monkeypatch.setattr(backtester, "get_stock_data", lambda ticker: yetersiz_veri)

    result = backtest_stock("AZ_VERI.IS")

    assert result == {}

# ---------------------------------------------------------
# raw_df parametresi ve timeframe desteği testleri
# ---------------------------------------------------------
def test_backtest_stock_uses_provided_raw_df_without_fetching(monkeypatch):
    """raw_df verildiğinde, backtest_stock'un get_stock_data'yı HİÇ çağırmadığını doğrular"""
    def get_stock_data_should_not_be_called(ticker):
        raise AssertionError("get_stock_data çağrılmamalıydı, raw_df verilmişti!")

    monkeypatch.setattr(backtester, "get_stock_data", get_stock_data_should_not_be_called)

    sahte_veri = _elle_hesaplanmis_ohlc_tablosu()
    # Hata fırlamazsa, get_stock_data hiç çağrılmamış demektir.
    result = backtest_stock("HERHANGI.IS", raw_df=sahte_veri)

    assert result != {}

def test_backtest_stock_without_raw_df_calls_get_stock_data(monkeypatch):
    """raw_df verilmediğinde (varsayılan davranış), backtest_stock'un get_stock_data'yı çağırdığını doğrular -geriye dönük uyumluluk."""
    cagrildi = {"durum": False}

    def sahte_get_stock_data(ticker):
        cagrildi["durum"] = True
        return _elle_hesaplanmis_ohlc_tablosu()

    monkeypatch.setattr(backtester, "get_stock_data", sahte_get_stock_data)

    backtest_stock("HERHANGI.IS")  # raw_df verilmedi

    assert cagrildi["durum"] is True

def test_backtest_stock_weekly_timeframe_produces_fewer_samples_than_daily():
    """Aynı ham veriden, weekly timeframe'in daily'den daha az sample_size) 
    ürettiğini doğrular -resample'ın gerçekten uygulandığının kanıtıdır."""
    gun_sayisi = 60
    uzun_veri = pd.DataFrame({
        "Open": [100.0 + i for i in range(gun_sayisi)],
        "High": [105.0 + i for i in range(gun_sayisi)],
        "Low": [95.0 + i for i in range(gun_sayisi)],
        "Close": [102.0 + i for i in range(gun_sayisi)],
    }, index=pd.date_range("2026-01-01", periods=gun_sayisi, freq="B"))

    daily_result = backtest_stock("TEST.IS", timeframe="daily", raw_df=uzun_veri)
    weekly_result = backtest_stock("TEST.IS", timeframe="weekly", raw_df=uzun_veri)

    daily_n = daily_result["classic"]["PP"]["sample_size"]
    weekly_n = weekly_result["classic"]["PP"]["sample_size"]

    assert weekly_n < daily_n
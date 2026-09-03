import pandas as pd
import pytest
import alert_checker
from alert_checker import check_alert_condition, get_level_and_today_ohlc, run_alert_checks

# -------------------------------
# check_alert_condition testleri 
# -------------------------------
def test_check_alert_condition_touch_triggers():
    alert = {"method": "classic", "level_name": "R1", "condition_type": "touch"}
    pivots = {"classic": {"R1": 106.0}}
    today_ohlc = {"Open": 101.0, "High": 107.0, "Low": 95.0, "Close": 103.0}

    triggered, level = check_alert_condition(alert, pivots, today_ohlc)
    assert triggered is True
    assert level == 106.0

def test_check_alert_condition_touch_not_triggered():
    alert = {"method": "classic", "level_name": "R1", "condition_type": "touch"}
    pivots = {"classic": {"R1": 200.0}}
    today_ohlc = {"Open": 101.0, "High": 107.0, "Low": 95.0, "Close": 103.0}

    triggered, _ = check_alert_condition(alert, pivots, today_ohlc)
    assert triggered is False

def test_check_alert_condition_resistance_break():
    alert = {"method": "classic", "level_name": "R1", "condition_type": "break"}
    pivots = {"classic": {"R1": 100.0}}
    today_ohlc = {"Open": 99.0, "High": 105.0, "Low": 98.0, "Close": 103.0}

    triggered, _ = check_alert_condition(alert, pivots, today_ohlc)
    assert triggered is True

def test_check_alert_condition_pp_break_is_directionless():
    alert = {"method": "classic", "level_name": "PP", "condition_type": "break"}
    pivots = {"classic": {"PP": 100.0}}

    triggered_up, _ = check_alert_condition(
        alert, pivots, {"Open": 99.0, "High": 105.0, "Low": 98.0, "Close": 103.0}
    )
    assert triggered_up is True

    triggered_flat, _ = check_alert_condition(
        alert, pivots, {"Open": 100.0, "High": 100.1, "Low": 99.9, "Close": 100.0}
    )
    assert triggered_flat is False

def test_check_alert_condition_missing_level_returns_false():
    """DeMark'ta R2 yok -method/level kombinasyonu bulunamazsa güvenle False dönmeli."""
    alert = {"method": "demark", "level_name": "R2", "condition_type": "touch"}
    pivots = {"demark": {"PP": 100.0, "R1": 105.0, "S1": 95.0}}
    today_ohlc = {"Open": 100.0, "High": 106.0, "Low": 94.0, "Close": 100.0}

    triggered, level = check_alert_condition(alert, pivots, today_ohlc)
    assert triggered is False
    assert level is None

# ---------------------------------------------------------
# get_level_and_today_ohlc testleri
# ---------------------------------------------------------
def test_get_level_and_today_ohlc_daily_uses_fast_info(monkeypatch):
    raw_df = pd.DataFrame({
        "Open": [100.0, 101.0], "High": [105.0, 106.0],
        "Low": [95.0, 96.0], "Close": [102.0, 103.0],
    }, index=pd.date_range("2026-01-01", periods=2))

    fake_fi = {"open": 104.0, "dayHigh": 108.0, "dayLow": 103.0, "lastPrice": 106.0}

    class FakeTicker:
        def __init__(self, ticker):
            self.fast_info = fake_fi

    monkeypatch.setattr(alert_checker.yf, "Ticker", FakeTicker)

    cache = {}
    pivots, today_ohlc = get_level_and_today_ohlc("TEST.IS", "daily", raw_df, cache)

    assert today_ohlc["High"] == 108.0
    assert today_ohlc["Low"] == 103.0
    assert today_ohlc["Close"] == 106.0
    assert "classic" in pivots
    assert "TEST.IS" in cache  # fast_info cachelenmis, tekrar çekilmeyecek

def test_get_level_and_today_ohlc_daily_returns_none_on_fetch_failure(monkeypatch):
    """Canlı veri çekilemezse (ağ hatası), çökmeden (None, None) dönmeli."""
    raw_df = pd.DataFrame(
        {"Open": [100.0], "High": [105.0], "Low": [95.0], "Close": [102.0]},
        index=pd.date_range("2026-01-01", periods=1),
    )

    class FailingTicker:
        def __init__(self, ticker):
            raise ConnectionError("simulated network failure")

    monkeypatch.setattr(alert_checker.yf, "Ticker", FailingTicker)

    pivots, today_ohlc = get_level_and_today_ohlc("TEST.IS", "daily", raw_df, {})
    assert pivots is None
    assert today_ohlc is None

def test_get_level_and_today_ohlc_weekly_uses_resample():
    """Weekly/monthly için canlı veri değil, resample edilmiş geçmiş veri kullanılmalı."""
    raw_df = pd.DataFrame({
        "Open": [100.0 + i for i in range(20)],
        "High": [105.0 + i for i in range(20)],
        "Low": [95.0 + i for i in range(20)],
        "Close": [102.0 + i for i in range(20)],
    }, index=pd.date_range("2026-01-01", periods=20, freq="B"))

    pivots, today_ohlc = get_level_and_today_ohlc("TEST.IS", "weekly", raw_df, {})

    assert pivots is not None
    assert "classic" in pivots
    assert today_ohlc is not None

# ---------------------------------------------------------
# run_alert_checks uçtan uca testleri (tamamen mocklu)
# ---------------------------------------------------------
def _fake_fast_info():
    return {"open": 101.0, "dayHigh": 107.0, "dayLow": 98.0, "lastPrice": 103.0}

def test_run_alert_checks_sends_message_and_marks_triggered(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # log dosyası gerçek proje klasörünü kirletmesin

    fake_alerts = pd.DataFrame([{
        "id": 1, "user_id": 1, "ticker": "AAA.IS", "method": "classic", "timeframe": "daily",
        "level_name": "R1", "condition_type": "touch", "last_triggered_date": None,
        "telegram_chat_id": "111", "username": "user1",
    }])
    monkeypatch.setattr(alert_checker, "get_all_active_alerts_with_contact", lambda: fake_alerts)

    raw_df = pd.DataFrame(
        {"Open": [100.0], "High": [105.0], "Low": [95.0], "Close": [100.0]},
        index=pd.date_range("2026-01-01", periods=1),
    )
    monkeypatch.setattr(alert_checker, "get_stock_data", lambda ticker: raw_df)

    class FakeTicker:
        def __init__(self, ticker):
            self.fast_info = _fake_fast_info()

    monkeypatch.setattr(alert_checker.yf, "Ticker", FakeTicker)

    sent_messages = []
    monkeypatch.setattr(
        alert_checker, "send_telegram_message",
        lambda chat_id, text: sent_messages.append((chat_id, text)) or True,
    )

    marked = []
    monkeypatch.setattr(alert_checker, "mark_alert_triggered", lambda aid, d: marked.append((aid, d)))

    run_alert_checks()

    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "111"
    assert len(marked) == 1
    assert marked[0][0] == 1

def test_run_alert_checks_skips_already_triggered_today(monkeypatch, tmp_path):
    """Bugün zaten tetiklenmiş bir alert TEKRAR mesaj göndermemeli."""
    monkeypatch.chdir(tmp_path)

    from datetime import date
    today_str = date.today().isoformat()

    fake_alerts = pd.DataFrame([{
        "id": 2, "user_id": 1, "ticker": "AAA.IS", "method": "classic", "timeframe": "daily",
        "level_name": "R1", "condition_type": "touch", "last_triggered_date": today_str,
        "telegram_chat_id": "111", "username": "user1",
    }])
    monkeypatch.setattr(alert_checker, "get_all_active_alerts_with_contact", lambda: fake_alerts)

    raw_df = pd.DataFrame(
        {"Open": [100.0], "High": [105.0], "Low": [95.0], "Close": [100.0]},
        index=pd.date_range("2026-01-01", periods=1),
    )
    monkeypatch.setattr(alert_checker, "get_stock_data", lambda ticker: raw_df)

    class FakeTicker:
        def __init__(self, ticker):
            self.fast_info = _fake_fast_info()

    monkeypatch.setattr(alert_checker.yf, "Ticker", FakeTicker)

    sent_messages = []
    monkeypatch.setattr(
        alert_checker, "send_telegram_message",
        lambda chat_id, text: sent_messages.append((chat_id, text)) or True,
    )
    monkeypatch.setattr(alert_checker, "mark_alert_triggered", lambda aid, d: None)

    run_alert_checks()

    assert len(sent_messages) == 0  # spam önleme çalışmalı

def test_run_alert_checks_handles_no_active_alerts(monkeypatch, tmp_path):
    """Hiç aktif alert yoksa, hata fırlatmadan sessizce çıkmalı."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(alert_checker, "get_all_active_alerts_with_contact", lambda: pd.DataFrame())

    run_alert_checks()  # hata fırlatmamalı
"""
pivot_calculations.py modülündeki 5 pivot yöntemi test edilir.
"""
import pytest

from pivot_calculations import (
    classic_pivot,
    fibonacci_pivot,
    camarilla_pivot,
    demark_pivot,
    woodie_pivot,
    calculate_all_pivots,
)

PREV_OPEN = 100.0
PREV_HIGH = 105.0
PREV_LOW = 98.0
PREV_CLOSE = 103.0
TODAY_OPEN = 103.5

def test_classic_pivot():
    result = classic_pivot(PREV_HIGH, PREV_LOW, PREV_CLOSE)
    assert result["PP"] == pytest.approx(102.00, abs=0.01)
    assert result["R1"] == pytest.approx(106.00, abs=0.01)
    assert result["R2"] == pytest.approx(109.00, abs=0.01)
    assert result["R3"] == pytest.approx(113.00, abs=0.01)
    assert result["S1"] == pytest.approx(99.00, abs=0.01)
    assert result["S2"] == pytest.approx(95.00, abs=0.01)
    assert result["S3"] == pytest.approx(92.00, abs=0.01)

def test_fibonacci_pivot():
    result = fibonacci_pivot(PREV_HIGH, PREV_LOW, PREV_CLOSE)
    assert result["PP"] == pytest.approx(102.00, abs=0.01)
    assert result["R1"] == pytest.approx(104.67, abs=0.01)
    assert result["R2"] == pytest.approx(106.33, abs=0.01)
    assert result["R3"] == pytest.approx(109.00, abs=0.01)
    assert result["S1"] == pytest.approx(99.33, abs=0.01)
    assert result["S2"] == pytest.approx(97.67, abs=0.01)
    assert result["S3"] == pytest.approx(95.00, abs=0.01)

def test_camarilla_pivot():
    result = camarilla_pivot(PREV_HIGH, PREV_LOW, PREV_CLOSE)
    assert result["PP"] == pytest.approx(103.00, abs=0.01)
    assert result["R1"] == pytest.approx(103.64, abs=0.01)
    assert result["R2"] == pytest.approx(104.28, abs=0.01)
    assert result["R3"] == pytest.approx(104.92, abs=0.01)
    assert result["S1"] == pytest.approx(102.36, abs=0.01)
    assert result["S2"] == pytest.approx(101.72, abs=0.01)
    assert result["S3"] == pytest.approx(101.08, abs=0.01)

def test_demark_pivot_close_greater_than_open():
    """close(103) > open(100)"""
    result = demark_pivot(PREV_OPEN, PREV_HIGH, PREV_LOW, PREV_CLOSE)
    assert result["PP"] == pytest.approx(102.75, abs=0.01)
    assert result["R1"] == pytest.approx(107.50, abs=0.01)
    assert result["S1"] == pytest.approx(100.50, abs=0.01)

def test_demark_pivot_close_less_than_open():
    """
    close < open
    X = High + 2*Low + Close = 105 + 2*98 + 95 = 396
    """
    result = demark_pivot(open_=100.0, high=105.0, low=98.0, close=95.0)
    expected_pp = (105.0 + 2 * 98.0 + 95.0) / 4
    assert result["PP"] == pytest.approx(expected_pp, abs=0.01)

def test_demark_pivot_close_equals_open():
    """
    close == open
    X = High + Low + 2*Close = 105 + 98 + 2*100 = 403
    """
    result = demark_pivot(open_=100.0, high=105.0, low=98.0, close=100.0)
    expected_pp = (105.0 + 98.0 + 2 * 100.0) / 4
    assert result["PP"] == pytest.approx(expected_pp, abs=0.01)

def test_woodie_pivot_uses_today_open_not_prev_open():
    """İleride biri yanlışlıkla prev_open'ı Woodie'ye
    verirse testin FAILED olması sağlanır."""
    result = woodie_pivot(TODAY_OPEN, PREV_HIGH, PREV_LOW, PREV_CLOSE)
    assert result["PP"] == pytest.approx(102.50, abs=0.01)
    assert result["R1"] == pytest.approx(107.00, abs=0.01)
    assert result["R2"] == pytest.approx(109.50, abs=0.01)
    assert result["R3"] == pytest.approx(114.00, abs=0.01)
    assert result["S1"] == pytest.approx(100.00, abs=0.01)
    assert result["S2"] == pytest.approx(95.50, abs=0.01)
    assert result["S3"] == pytest.approx(93.00, abs=0.01)

    # Yanlışlıkla prev_open kullanılması PP'nin farklı çıkmasına sebep olur.(negatif kontrol).
    wrong_result = woodie_pivot(PREV_OPEN, PREV_HIGH, PREV_LOW, PREV_CLOSE)
    assert wrong_result["PP"] != pytest.approx(result["PP"], abs=0.01)

def test_calculate_all_pivots_returns_all_five_methods():
    """calculate_all_pivots'un 5 yöntemin tümünü döndürdüğü doğrulanır."""
    result = calculate_all_pivots(
        prev_open=PREV_OPEN, prev_high=PREV_HIGH,
        prev_low=PREV_LOW, prev_close=PREV_CLOSE,
        today_open=TODAY_OPEN,
    )
    assert set(result.keys()) == {"classic", "fibonacci", "camarilla", "demark", "woodie"}

def test_calculate_all_pivots_woodie_gets_today_open():
    """calculate_all_pivots üzerinden çağrıldığında da Woodie'nin
    today_open'ı doğru şekilde aldığı doğrulanır (entegrasyon testi)."""
    result = calculate_all_pivots(
        prev_open=PREV_OPEN, prev_high=PREV_HIGH,
        prev_low=PREV_LOW, prev_close=PREV_CLOSE,
        today_open=TODAY_OPEN,
    )
    assert result["woodie"]["PP"] == pytest.approx(102.50, abs=0.01)

def test_calculate_all_pivots_without_today_open_falls_back_to_prev_open():
    """today_open verilmezse, Woodie'nin prev_open'a "yaklaşık" olarak düştüğü doğrulanır."""
    result = calculate_all_pivots(
        prev_open=PREV_OPEN, prev_high=PREV_HIGH,
        prev_low=PREV_LOW, prev_close=PREV_CLOSE,
    )
    fallback_woodie = woodie_pivot(PREV_OPEN, PREV_HIGH, PREV_LOW, PREV_CLOSE)
    assert result["woodie"]["PP"] == pytest.approx(fallback_woodie["PP"], abs=0.01)

def test_demark_has_no_r2_r3_s2_s3():
    """DeMark'ın yapısı gereği sadece PP/R1/S1 ürettiğini, R2/R3/S2/S3 ürettiğinin SANILMADIĞINI doğrular."""
    result = demark_pivot(PREV_OPEN, PREV_HIGH, PREV_LOW, PREV_CLOSE)
    assert set(result.keys()) == {"PP", "R1", "S1"}
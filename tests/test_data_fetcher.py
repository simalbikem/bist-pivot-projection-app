"""
Strateji: Çoğunlukla MOCK testler kullanılmaktadır (yfinance'i gerçekten
çağırmadan, sahte veriyle) -adece 1 tane GERÇEK bağlantı testi vardır.
"""
import pandas as pd
import pytest

import data_fetcher
from data_fetcher import get_stock_data, get_multiple_stocks_data

def _sahte_ohlcv_tablosu() -> pd.DataFrame:
    return pd.DataFrame({
        "Open": [100.0, 101.0, 102.0],
        "High": [105.0, 106.0, 107.0],
        "Low": [98.0, 99.0, 100.0],
        "Close": [103.0, 104.0, 105.0],
        "Volume": [1000, 1100, 1200],
    })

def test_get_stock_data_returns_dataframe_on_success(monkeypatch):
    sahte_veri = _sahte_ohlcv_tablosu()

    def sahte_download(*args, **kwargs):
        return sahte_veri

    monkeypatch.setattr(data_fetcher.yf, "download", sahte_download)

    result = get_stock_data("SAHTE.IS")

    assert not result.empty
    assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(result) == 3

def test_get_stock_data_flattens_multiindex_columns(monkeypatch):
    """yfinance bazen MultiIndex sütun döndürür -kodun bunu tek seviyeye düzleştirdiğini doğrular."""
    sahte_veri = _sahte_ohlcv_tablosu()
    sahte_veri.columns = pd.MultiIndex.from_product([sahte_veri.columns, ["SAHTE.IS"]])

    def sahte_download(*args, **kwargs):
        return sahte_veri

    monkeypatch.setattr(data_fetcher.yf, "download", sahte_download)

    result = get_stock_data("SAHTE.IS")

    # Düzleştirme sonrası sütunlar tekrar tek seviyeli olmalıdır.
    assert not isinstance(result.columns, pd.MultiIndex)
    assert "Open" in result.columns

def test_get_stock_data_returns_empty_dataframe_when_no_data(monkeypatch):
    """yfinance boş bir tablo döndürdüğünde, get_stock_data'nın 
    hata fırlatmadan boş DataFrame döndürdüğünü doğrular."""
    def sahte_download(*args, **kwargs):
        return pd.DataFrame()  # boş tablo

    monkeypatch.setattr(data_fetcher.yf, "download", sahte_download)

    result = get_stock_data("GECERSIZ.IS")

    assert result.empty

def test_get_stock_data_handles_exception_gracefully(monkeypatch):
    """yfinance bir hata fırlattığında, get_stock_data'nın 
    programı çökertmeden boş DataFrame döndürdüğünü doğrular."""
    def sahte_download(*args, **kwargs):
        raise ConnectionError("Sahte bağlantı hatası")

    monkeypatch.setattr(data_fetcher.yf, "download", sahte_download)

    result = get_stock_data("HERHANGI.IS")

    assert result.empty

def test_get_multiple_stocks_data_returns_dict_with_all_tickers(monkeypatch):
    """get_multiple_stocks_data'nın, verilen her ticker için bir sözlük girdisi ürettiğini doğrular. 
    Burada get_stock_data'nın kendisi mocklanır (bir alt seviye yukarı çıkarak), çünkü bu fonksiyonun 
    kendi mantığı (döngü + sözlük oluşturma) test edilmek istenmektedir, yfinance detayları değil."""
    def sahte_get_stock_data(ticker, years=2):
        return _sahte_ohlcv_tablosu()

    monkeypatch.setattr(data_fetcher, "get_stock_data", sahte_get_stock_data)

    tickers = ["AAA.IS", "BBB.IS"]
    result = get_multiple_stocks_data(tickers)

    assert set(result.keys()) == {"AAA.IS", "BBB.IS"}
    assert not result["AAA.IS"].empty
    assert not result["BBB.IS"].empty

@pytest.mark.slow
def test_get_stock_data_real_connection():
    """ Yahoo Finance'e erişim doğrulanır."""
    from config import BIST_STOCKS

    result = get_stock_data(BIST_STOCKS[0])

    assert not result.empty
    assert "Close" in result.columns
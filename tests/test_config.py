import pytest
import config
from config import get_secret

def test_get_secret_returns_env_variable_when_present(monkeypatch):
    """Ortam değişkeni varsa, doğrudan o döndürülür."""
    monkeypatch.setenv("TEST_SECRET_KEY", "env_degeri")

    result = get_secret("TEST_SECRET_KEY")

    assert result == "env_degeri"

def test_get_secret_falls_back_to_streamlit_secrets_when_env_missing(monkeypatch):
    """Ortam değişkeni yoksa, st.secrets'a düşülür. 
    st.secrets'ı gerçek Streamlit çalıştırmadan simüle etmek için sahte bir modül kullanıılır."""
    monkeypatch.delenv("TEST_SECRET_KEY", raising=False)

    class FakeSecrets:
        def get(self, key):
            return "bulut_degeri" if key == "TEST_SECRET_KEY" else None

    class FakeStreamlit:
        secrets = FakeSecrets()

    monkeypatch.setattr(config, "st", FakeStreamlit(), raising=False)
    # get_secret fonksiyonu "import streamlit as st" işlemini kendi içinde yapıyor
    # -bunu simüle etmek için sys.modules'e sahte modülü enjekte ediyoruz.
    import sys
    monkeypatch.setitem(sys.modules, "streamlit", FakeStreamlit())

    result = get_secret("TEST_SECRET_KEY")

    assert result == "bulut_degeri"

def test_get_secret_returns_none_when_neither_source_has_it(monkeypatch):
    """Ne ortam değişkeninde ne de st.secretsta varsa, None dönüp hata fırlatmamalı."""
    monkeypatch.delenv("TEST_SECRET_KEY", raising=False)

    class FakeSecrets:
        def get(self, key):
            return None

    class FakeStreamlit:
        secrets = FakeSecrets()

    import sys
    monkeypatch.setitem(sys.modules, "streamlit", FakeStreamlit())

    result = get_secret("TEST_SECRET_KEY")

    assert result is None

def test_get_secret_returns_none_when_streamlit_not_available(monkeypatch):
    monkeypatch.delenv("TEST_SECRET_KEY", raising=False)

    import sys

    class BrokenStreamlit:
        @property
        def secrets(self):
            raise FileNotFoundError("secrets.toml bulunamadı")

    monkeypatch.setitem(sys.modules, "streamlit", BrokenStreamlit())

    result = get_secret("TEST_SECRET_KEY")

    assert result is None
"""
Pytest için global fixturelar.
"""

import pytest

@pytest.fixture(autouse=True, scope="session")
def force_local_database_for_tests(monkeypatch_session=None):
    """Tüm test oturumları için USE_TURSOyu zorla 'false' yapar.
    autouse=True sayesinde her test dosyasında otomatik uygulanır, hiçbir test dosyasının bunu ayrıca import etmesi gerekmez."""
    import os
    original_value = os.environ.get("USE_TURSO")
    os.environ["USE_TURSO"] = "false"
    yield
    # Test oturumu bitince orijinal değeri geri yükler.
    if original_value is not None:
        os.environ["USE_TURSO"] = original_value
    else:
        os.environ.pop("USE_TURSO", None)
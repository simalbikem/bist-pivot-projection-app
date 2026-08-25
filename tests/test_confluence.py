import pytest

from confluence import collect_levels, find_confluence_zones

def test_collect_levels_flattens_dict_correctly():
    """collect_levels'ın iç içe dict'i düz bir listeye çevirdiği doğrulanır."""
    pivot_results = {
        "classic": {"PP": 100.0, "R1": 105.0},
        "fibonacci": {"PP": 100.2},
    }

    flat = collect_levels(pivot_results)

    assert len(flat) == 3
    assert {"method": "classic", "level": "PP", "value": 100.0} in flat
    assert {"method": "classic", "level": "R1", "value": 105.0} in flat
    assert {"method": "fibonacci", "level": "PP", "value": 100.2} in flat

def test_find_confluence_zones_groups_close_values_from_different_methods():
    """İki farklı yöntemin birbirine yakın seviyeleri, 
    tek bir confluence zone olarak gruplanmalıdır."""
    pivot_results = {
        "classic": {"PP": 100.0},
        "fibonacci": {"PP": 100.1},   # classic'e çok yakın (%0.1 fark)
        "camarilla": {"PP": 150.0},   # tamamen uzak
    }

    zones = find_confluence_zones(pivot_results, tolerance_pct=0.003, min_methods=2)

    assert len(zones) == 1
    assert zones[0]["method_count"] == 2
    methods_in_zone = {c["method"] for c in zones[0]["contributors"]}
    assert methods_in_zone == {"classic", "fibonacci"}

def test_find_confluence_zones_excludes_single_method_clusters():
    """Aynı yöntemin kendi seviyeleri birbirine yakın olsa bile, 
    TEK bir yöntem olduğu için confluence zone SAYILMAMALIdır."""
    pivot_results = {
        "classic": {"R1": 100.0, "R2": 100.1},  # aynı yöntem, çok yakın
    }

    zones = find_confluence_zones(pivot_results, tolerance_pct=0.003, min_methods=2)

    assert len(zones) == 0

def test_find_confluence_zones_respects_min_methods_parameter():
    """min_methods=3 verildiğinde, sadece 2 yöntemden oluşan bir kümenin 
    zone sayılmadığı doğrulanır."""
    pivot_results = {
        "classic": {"PP": 100.0},
        "fibonacci": {"PP": 100.1},
        "camarilla": {"PP": 200.0},
    }

    zones_min2 = find_confluence_zones(pivot_results, tolerance_pct=0.003, min_methods=2)
    zones_min3 = find_confluence_zones(pivot_results, tolerance_pct=0.003, min_methods=3)

    assert len(zones_min2) == 1  # classic + fibonacci yeterli
    assert len(zones_min3) == 0  # 3 farklı yöntem yok

def test_find_confluence_zones_sorted_by_method_count_descending():
    """Birden fazla zone bulunduğunda, en çok yönteme sahip olanın
    listenin başında olduğu doğrulanır."""
    pivot_results = {
        "classic":   {"PP": 100.0, "R1": 200.0},
        "fibonacci": {"PP": 100.1, "R1": 200.1},
        "camarilla": {"PP": 100.2},  # sadece PP bölgesine katkı verir
    }

    zones = find_confluence_zones(pivot_results, tolerance_pct=0.003, min_methods=2)

    assert len(zones) == 2
    assert zones[0]["method_count"] >= zones[1]["method_count"]
    # PP bölgesi 3 yöntemli olmalı
    assert zones[0]["method_count"] == 3

def test_find_confluence_zones_returns_empty_list_when_no_confluence():
    """Hiçbir seviye birbirine yakın değilse, boş liste dönmelidir."""
    pivot_results = {
        "classic": {"PP": 100.0},
        "fibonacci": {"PP": 500.0},
    }

    zones = find_confluence_zones(pivot_results, tolerance_pct=0.003, min_methods=2)

    assert zones == []
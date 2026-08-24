"""
Farklı pivot algoritmalarından gelen seviyelerin (PP, R1-R3, S1-S3) birbirine yakın düştüğü "confluence zones" tespit edilir.
Mantık: Eğer 2 veya daha fazla FARKLI yöntem, birbirine CONFLUENCE_TOLERANCE_PCT kadar yakın bir seviye üretiyorsa, bu bölge "confluence zone" sayılır.
"""
from config import CONFLUENCE_TOLERANCE_PCT

def collect_levels(pivot_results: dict) -> list:
    flat_list = []
    for method, levels in pivot_results.items():
        for level_name, value in levels.items():
            flat_list.append({
                "method": method,
                "level": level_name,
                "value": value,
            })
    return flat_list

def find_confluence_zones(
    pivot_results: dict,
    tolerance_pct: float = CONFLUENCE_TOLERANCE_PCT,
    min_methods: int = 2,
) -> list:

    all_levels = collect_levels(pivot_results)

    # Değere göre küçükten büyüğe sıralar - clustering işlemini kolaylaştırılır.
    all_levels.sort(key=lambda x: x["value"])

    raw_clusters = []
    current_cluster = [all_levels[0]]

    for item in all_levels[1:]:
        # Mevcut kümenin ortalamasına göre yakınlık kontrol edilir.
        cluster_avg = sum(c["value"] for c in current_cluster) / len(current_cluster)
        relative_diff = abs(item["value"] - cluster_avg) / cluster_avg

        if relative_diff <= tolerance_pct:
            # Yeterince yakınsa, aynı kümeye ekler.
            current_cluster.append(item)
        else:
            # Yeterince uzaksa, mevcut kümeyi kapatır, yeni küme başlatır.
            raw_clusters.append(current_cluster)
            current_cluster = [item]

    raw_clusters.append(current_cluster)  # son kümeyi de ekler.

    # Sadece min_methods sayısından fazla FARKLI yöntem içeren kümeleri confluence zone sayar.
    confluence_zones = []
    for cluster in raw_clusters:
        distinct_methods = set(c["method"] for c in cluster)
        if len(distinct_methods) >= min_methods:
            center = sum(c["value"] for c in cluster) / len(cluster)
            confluence_zones.append({
                "center": center,
                "method_count": len(distinct_methods),
                "contributors": cluster,
            })

    # En güçlü bölgeler en üstte sıralanır.
    confluence_zones.sort(key=lambda z: z["method_count"], reverse=True)

    return confluence_zones


# Hızlı test
if __name__ == "__main__":
    from pivot_calculations import calculate_all_pivots

    prev_open, prev_high, prev_low, prev_close = 100.0, 105.0, 98.0, 103.0
    today_open = 103.5

    pivots = calculate_all_pivots(
        prev_open, prev_high, prev_low, prev_close, today_open
    )

    zones = find_confluence_zones(pivots)

    print(f"{len(zones)} confluence zone bulundu:\n")
    for i, zone in enumerate(zones, start=1):
        print(f"Zone {i}: merkez={zone['center']:.2f}, "
              f"{zone['method_count']} farklı yöntem")
        for c in zone["contributors"]:
            print(f"    - {c['method']} {c['level']}: {c['value']:.2f}")
        print()
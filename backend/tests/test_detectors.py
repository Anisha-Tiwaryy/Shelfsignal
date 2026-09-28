"""Unit tests: detectors on tiny hand-built frames (no database)."""
import datetime as dt

import pandas as pd

from shelf import brief, detectors as D

START = dt.date(2025, 10, 1)


def frame(rows):
    return pd.DataFrame(rows, columns=["store", "city", "sku", "visit_date", "in_stock", "price", "pack_grams"])


def series(store, sku, grams, prices, city="Delhi", every=14, start=START):
    return [(store, city, sku, start + dt.timedelta(days=i * every), True, p, g)
            for i, (g, p) in enumerate(zip(grams, prices))]


def test_confirmed_grams_drops_one_off_ocr_misread():
    assert D.confirmed_grams([100, 100, 10, 100, 100]) == [100, 100, None, 100, 100]


def test_single_misread_is_not_a_pack_change():
    rows = []
    for s in range(5):
        rows += series(f"S{s}", "A", [100, 100, 10, 100, 100, 100], [20] * 6)
    assert D.detect_pack_changes(frame(rows)) == []


def test_shrinkflation_detected_when_pack_shrinks_and_price_holds():
    rows = []
    for s in range(5):
        rows += series(f"S{s}", "A", [100, 100, 100, 90, 90, 90], [20] * 6)
    [r] = D.detect_pack_changes(frame(rows))
    assert r["kind"] == "shrinkflation"
    assert (r["grams_before"], r["grams_after"]) == (100, 90)
    assert round(r["per_gram_change_pct"], 1) == 11.1
    assert r["confidence"] == 1.0


def test_proportional_resize_is_not_shrinkflation():
    rows = []
    for s in range(5):
        rows += series(f"S{s}", "A", [100, 100, 100, 80, 80, 80], [50, 50, 50, 40, 40, 40])
    [r] = D.detect_pack_changes(frame(rows))
    assert r["kind"] == "resize"


def test_price_hike_without_pack_change_is_ignored():
    rows = []
    for s in range(5):
        rows += series(f"S{s}", "A", [100] * 6, [20, 20, 20, 22, 22, 22])
    assert D.detect_pack_changes(frame(rows)) == []


def test_change_in_too_few_stores_is_not_reported():
    rows = []
    for s in range(20):
        grams = [100, 100, 100, 90, 90, 90] if s < 2 else [100] * 6
        rows += series(f"S{s}", "A", grams, [20] * 6)
    assert D.detect_pack_changes(frame(rows)) == []


def test_launch_ignores_products_already_on_shelf_and_measures_spread():
    rows = []
    for s in range(4):
        rows += series(f"S{s}", "OLD", [100] * 20, [20] * 20)
    launch_day = START + dt.timedelta(days=100)
    for s, delay in enumerate([0, 7, 28]):  # 3 of 4 stores adopt
        rows += series(f"S{s}", "NEW", [50] * 5, [10] * 5, start=launch_day + dt.timedelta(days=delay))
    [r] = D.detect_launches(frame(rows), START)
    assert r["sku"] == "NEW"
    assert r["days_to_25"] == 0 and r["days_to_50"] == 7
    assert r["reach_pct"] == 75.0


def test_per_gram_index_exposes_shrinkflation_that_pack_index_misses():
    rows = []
    for s in range(3):
        for m in range(3):
            d = dt.date(2025, 10 + m, 5)
            rows.append((f"S{s}", "Pune", "A", d, True, 10.0, 100 if m == 0 else 80))
    idx = D.price_index(frame(rows))
    last = [r for r in idx if r["month"] == "2025-12"][0]
    assert last["pack_index"] == 100.0
    assert last["per_gram_index"] == 125.0


def test_city_price_shock_flagged():
    rows = []
    for city, jump in [("A", 1.0), ("B", 1.0), ("C", 1.10)]:
        for m in range(6):
            p = 100 * (1.004 ** m) * (jump if m >= 4 else 1.0)
            rows.append(("S" + city, city, "X", dt.date(2025, 10, 5) + dt.timedelta(days=31 * m), True, p, 100))
    idx = D.price_index(frame(rows))
    assert [(r["city"], r["month"]) for r in idx if r["shock"]] == [("C", "2026-02")]


def test_template_brief_uses_only_detector_numbers():
    pack = [{"sku": "A", "kind": "shrinkflation", "grams_before": 100, "grams_after": 90,
             "per_gram_change_pct": 11.1, "confidence": 0.9}]
    f = brief.facts_from(pack, [], [])
    text = brief.template_brief(f)
    assert "100g to 90g" in text and "11.1%" in text

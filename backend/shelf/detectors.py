"""Signal detectors. Pure functions over a pandas DataFrame of observations
with columns: store, city, sku, visit_date, in_stock, price, pack_grams.

Kept free of Django so they are unit-testable in isolation and reusable in
a batch job, a notebook, or an API view.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

MIN_STORES = 3          # a pack change must be seen in at least this many stores
MIN_STORE_SHARE = 0.15  # ...and in at least this share of stores carrying the SKU
SHRINK_PER_GRAM = 0.05  # per-gram price rise that makes a pack cut "shrinkflation"
LAUNCH_BUFFER_DAYS = 45


# --------------------------------------------------------------------------
# 1. Pack changes (shrinkflation / resize / upsize)
# --------------------------------------------------------------------------
def confirmed_grams(grams: list[int]) -> list[int | None]:
    """Keep a pack-weight read only if the same value appears on an adjacent
    visit. A one-off OCR misread (100g read as 10g) never persists, a real
    pack change does, so this drops noise without a hand-tuned threshold."""
    out = []
    for i, g in enumerate(grams):
        prev_same = i > 0 and grams[i - 1] == g
        next_same = i + 1 < len(grams) and grams[i + 1] == g
        out.append(g if (prev_same or next_same) else None)
    return out


def store_changes(series: pd.DataFrame) -> list[dict]:
    """Change points in one store's series for one SKU (sorted by date)."""
    grams = series["pack_grams"].astype(int).tolist()
    prices = series["price"].astype(float).tolist()
    dates = series["visit_date"].tolist()
    conf = confirmed_grams(grams)
    points = [(i, g) for i, g in enumerate(conf) if g is not None]
    changes = []
    for (i0, a), (i1, b) in zip(points, points[1:]):
        if a == b:
            continue
        before = [prices[i] for i, g in points if g == a and i <= i0][-3:]
        after = [prices[i] for i, g in points if g == b and i >= i1][:3]
        changes.append({
            "grams_before": a, "grams_after": b, "date": dates[i1],
            "price_before": float(np.median(before)), "price_after": float(np.median(after)),
        })
    return changes


def detect_pack_changes(df: pd.DataFrame) -> list[dict]:
    live = df[df["in_stock"] & df["pack_grams"].notna()].sort_values("visit_date")
    results = []
    for sku, g in live.groupby("sku"):
        carrying = g["store"].nunique()
        found = []
        for store, s in g.groupby("store"):
            for c in store_changes(s):
                c["store"] = store
                found.append(c)
        if not found:
            continue
        fdf = pd.DataFrame(found)
        for (a, b), grp in fdf.groupby(["grams_before", "grams_after"]):
            n = grp["store"].nunique()
            if n < max(MIN_STORES, MIN_STORE_SHARE * carrying):
                continue
            price_chg = float(np.median(grp["price_after"] / grp["price_before"] - 1))
            per_gram = (1 + price_chg) * (a / b) - 1
            if b < a:
                kind = "shrinkflation" if per_gram >= SHRINK_PER_GRAM else "resize"
            else:
                kind = "upsize"
            results.append({
                "sku": sku, "kind": kind, "grams_before": int(a), "grams_after": int(b),
                "price_change_pct": round(price_chg * 100, 2),
                "per_gram_change_pct": round(per_gram * 100, 2),
                "first_seen": min(grp["date"]),
                "stores_changed": int(n), "stores_carrying": int(carrying),
                "confidence": round(n / carrying, 3),
            })
    return sorted(results, key=lambda r: (-r["per_gram_change_pct"], r["sku"]))


# --------------------------------------------------------------------------
# 2. Launch velocity
# --------------------------------------------------------------------------
def detect_launches(df: pd.DataFrame, dataset_start: dt.date | None = None) -> list[dict]:
    if df.empty:
        return []
    start = dataset_start or df["visit_date"].min()
    end = df["visit_date"].max()
    n_stores = df["store"].nunique()
    out = []
    for sku, g in df.groupby("sku"):
        first = g["visit_date"].min()
        if (first - start).days < LAUNCH_BUFFER_DAYS:
            continue  # already on shelves when observation began
        adopt = g.groupby("store")["visit_date"].min().map(lambda d: (d - first).days)
        horizon = (end - first).days
        curve, d25, d50 = [], None, None
        for day in range(0, horizon + 1, 7):
            share = float((adopt <= day).sum()) / n_stores
            curve.append([day, round(share, 3)])
            if d25 is None and share >= 0.25:
                d25 = day
            if d50 is None and share >= 0.5:
                d50 = day
        out.append({
            "sku": sku, "first_seen": first, "days_to_25": d25, "days_to_50": d50,
            "reach_pct": round(100 * len(adopt) / n_stores, 1), "curve": curve,
        })
    return sorted(out, key=lambda r: (r["days_to_50"] is None, r["days_to_50"] or 0))


# --------------------------------------------------------------------------
# 3. Shelf price index: pack price vs price per gram
# --------------------------------------------------------------------------
def price_index(df: pd.DataFrame, launch_skus: set[str] | None = None,
                shock_mult: float = 3.0, shock_floor: float = 0.025) -> list[dict]:
    """Monthly Jevons index per city, base = first month = 100.

    Two versions: on pack price (what CPI-style shelf tracking sees) and on
    price per gram (what the shopper actually pays). The gap between them is
    inflation hidden inside smaller packs.
    """
    launch_skus = launch_skus or set()
    live = df[df["in_stock"] & df["price"].notna() & ~df["sku"].isin(launch_skus)].copy()
    if live.empty:
        return []
    live["month"] = live["visit_date"].map(lambda d: d.strftime("%Y-%m"))
    live["ppg"] = live["price"] / live["pack_grams"]
    med = live.groupby(["city", "sku", "month"]).agg(price=("price", "median"), ppg=("ppg", "median")).reset_index()
    months = sorted(med["month"].unique())
    base_m = months[0]
    rows = []
    for city, g in med.groupby("city"):
        base = g[g["month"] == base_m].set_index("sku")
        for m in months:
            cur = g[g["month"] == m].set_index("sku")
            common = base.index.intersection(cur.index)
            if len(common) == 0:
                continue
            pi = float(np.exp(np.mean(np.log(cur.loc[common, "price"] / base.loc[common, "price"])))) * 100
            gi = float(np.exp(np.mean(np.log(cur.loc[common, "ppg"] / base.loc[common, "ppg"])))) * 100
            rows.append({"city": city, "month": m, "pack_index": round(pi, 2), "per_gram_index": round(gi, 2), "shock": False})

    # Shock = a month-on-month jump far above the typical move across all cities.
    idx = pd.DataFrame(rows).sort_values(["city", "month"])
    idx["mom"] = idx.groupby("city")["pack_index"].pct_change()
    typical = idx["mom"].abs().median()
    flag = (idx["mom"] > max(shock_floor, shock_mult * typical))
    rows_sorted = idx.to_dict("records")
    for r, f in zip(rows_sorted, flag.tolist()):
        r["shock"] = bool(f)
        r.pop("mom", None)
    return rows_sorted


# --------------------------------------------------------------------------
# Evaluation against planted ground truth
# --------------------------------------------------------------------------
def evaluate(pack: list[dict], launches: list[dict], index: list[dict], truth: dict) -> dict:
    planted = truth["pack_events"]
    true_shrink = {k for k, v in planted.items() if v["kind"] == "shrinkflation"}
    found_shrink = {r["sku"] for r in pack if r["kind"] == "shrinkflation"}
    tp = len(true_shrink & found_shrink)
    kind_ok = sum(1 for r in pack if r["sku"] in planted and planted[r["sku"]]["kind"] == r["kind"])
    false_packs = [r["sku"] for r in pack if r["sku"] not in planted or planted[r["sku"]]["kind"] == "price_hike"]
    launch_err = {}
    for r in launches:
        gt = truth["launches"].get(r["sku"])
        if gt and gt["days_to_50"] is not None and r["days_to_50"] is not None:
            launch_err[r["sku"]] = r["days_to_50"] - gt["days_to_50"]
    shocks = {(r["city"], r["month"]) for r in index if r["shock"]}
    gt_shock = (truth["shock"]["city"], truth["shock"]["month"])
    return {
        "shrinkflation_recall": tp / len(true_shrink) if true_shrink else None,
        "shrinkflation_precision": tp / len(found_shrink) if found_shrink else None,
        "pack_events_planted": sum(1 for v in planted.values() if v["kind"] != "price_hike"),
        "pack_events_kind_correct": kind_ok,
        "false_pack_signals": false_packs,
        "launches_found": len(launches),
        "launch_days_to_50_error": launch_err,
        "shock_found": gt_shock in shocks,
        "shock_false_alarms": sorted(shocks - {gt_shock}),
    }

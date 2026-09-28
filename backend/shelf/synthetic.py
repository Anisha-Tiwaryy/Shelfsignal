"""Synthetic shelf-audit data with planted, known events.

Stands in for the structured output an image-recognition pipeline produces
from field-rep shelf photos. Because every event is planted, each detector
can be scored against ground truth instead of eyeballed.

Planted:
  * 6 shrinkflation events (pack shrinks, shelf price unchanged), 2 on fixed-MRP packs
  * 2 proportional resizes (pack and price both shrink; NOT shrinkflation)
  * 1 upsize (pack and price both grow)
  * 2 plain price hikes (price up, pack unchanged; NOT a pack change)
  * 4 new-product launches with different adoption speeds
  * 1 city price shock (Kolkata, +4% from 2026-05)
  * OCR noise: ~1.5% of pack-weight reads are misread (dropped/added digit)
"""
from __future__ import annotations

import datetime as dt
import math
import random
from dataclasses import dataclass, field

START = dt.date(2025, 10, 1)
DAYS = 365
CITIES = ["Bengaluru", "Mumbai", "Delhi", "Kolkata", "Hyderabad"]
SHOCK_CITY, SHOCK_MONTH = "Kolkata", "2026-05"

# category: (grams range, price range in Rs)
CATEGORIES = {
    "biscuits": ((50, 250), (10, 60)),
    "noodles": ((70, 280), (14, 60)),
    "chips": ((25, 90), (10, 50)),
    "detergent": ((500, 1000), (60, 220)),
    "soap": ((75, 150), (30, 70)),
    "chocolate": ((20, 150), (10, 120)),
    "tea": ((100, 500), (60, 280)),
    "shampoo": ((80, 340), (60, 250)),
}
BRANDS = ["Aurel", "Brixa", "Corvo", "Dhanvi", "Elmora", "Fenwick", "Gaurika", "Halden"]
PRICE_POINTS = [5, 10, 20]  # small packs sold at fixed MRP points


@dataclass
class Dataset:
    stores: list = field(default_factory=list)
    skus: list = field(default_factory=list)
    observations: list = field(default_factory=list)
    truth: dict = field(default_factory=dict)


def _round5(x: float) -> int:
    return max(5, int(round(x / 5.0)) * 5)


def month_key(d: dt.date) -> str:
    return d.strftime("%Y-%m")


def month_index(d: dt.date) -> int:
    return (d.year - START.year) * 12 + d.month - START.month


def generate(n_stores: int = 90, n_existing: int = 36, seed: int = 7, ocr_noise: float = 0.015,
             visit_every: int = 14) -> Dataset:
    rng = random.Random(seed)
    ds = Dataset()

    # Stores
    for i in range(n_stores):
        city = CITIES[i % len(CITIES)]
        ds.stores.append({
            "code": f"ST{i + 1:03d}",
            "city": city,
            "channel": "modern_trade" if rng.random() < 0.3 else "kirana",
            "offset": rng.randrange(visit_every),
        })

    # SKUs (existing catalogue + 4 launches)
    cats = list(CATEGORIES)
    for i in range(n_existing + 4):
        cat = cats[i % len(cats)]
        (glo, ghi), (plo, phi) = CATEGORIES[cat]
        grams = _round5(rng.uniform(glo, ghi))
        price = rng.uniform(plo, phi)
        if price <= 22:
            price = min(PRICE_POINTS, key=lambda p: abs(p - price))
            fixed = True
        else:
            price = round(price)
            fixed = False
        ds.skus.append({
            "code": f"SKU{i + 1:03d}",
            "brand": BRANDS[i % len(BRANDS)],
            "category": cat,
            "name": f"{BRANDS[i % len(BRANDS)]} {cat.title()} {grams}g",
            "grams": grams,
            "price": float(price),
            "fixed_mrp": fixed,
            "carry": rng.uniform(0.75, 1.0),
            "launch": i >= n_existing,
        })

    existing = [s for s in ds.skus if not s["launch"]]
    launches = [s for s in ds.skus if s["launch"]]
    pool = existing[:]
    rng.shuffle(pool)
    # Fixed-MRP packs (Rs 5/10/20) cannot raise price, so real shrinkflation
    # concentrates there: put two of them first so they get shrink events.
    fixed = [s for s in pool if s["fixed_mrp"]][:2]
    pool = fixed + [s for s in pool if s not in fixed]

    # Planted pack / price events: (kind, grams multiplier, price multiplier)
    plan = ([("shrinkflation", None, 1.0)] * 6 + [("resize", 0.8, 0.8)] * 2
            + [("upsize", 1.25, 1.25)] + [("price_hike", 1.0, 1.10)] * 2)
    events = {}
    for (kind, gmul, pmul), sku in zip(plan, pool):
        if kind == "shrinkflation":
            gmul = rng.choice([0.85, 0.875, 0.9, 0.92])
        new_grams = _round5(sku["grams"] * gmul) if kind != "price_hike" else sku["grams"]
        if new_grams == sku["grams"] and kind != "price_hike":
            new_grams = sku["grams"] - 5
        events[sku["code"]] = {
            "kind": kind,
            "day": rng.randrange(90, 250),
            "grams_before": sku["grams"],
            "grams_after": new_grams,
            "price_mult": pmul,
        }

    # Launch adoption: mean days to adopt per store
    launch_speed = [15, 40, 90, 60]
    launch_meta = {}
    for sku, mean_days in zip(launches, launch_speed):
        launch_meta[sku["code"]] = {"day": rng.randrange(110, 200), "mean_days": mean_days}

    # City inflation (monthly) + planted shock
    city_rate = {c: rng.uniform(0.003, 0.006) for c in CITIES}

    def inflation(city: str, d: dt.date) -> float:
        f = (1 + city_rate[city]) ** month_index(d)
        if city == SHOCK_CITY and month_key(d) >= SHOCK_MONTH:
            f *= 1.04
        return f

    truth_launch = {}
    obs = []
    img = 0
    for store in ds.stores:
        # store-level switch dates for pack events (old stock sells through)
        switch = {code: ev["day"] + rng.randrange(0, 36) for code, ev in events.items()}
        adopt = {}
        for code, meta in launch_meta.items():
            if rng.random() < 0.8:
                adopt[code] = meta["day"] + int(rng.expovariate(1 / meta["mean_days"]))
        for code in launch_meta:
            truth_launch.setdefault(code, []).append(adopt.get(code))
        carries = {s["code"]: (rng.random() < s["carry"]) for s in existing}
        noise = {s["code"]: rng.lognormvariate(0, 0.015) for s in ds.skus}

        day = store["offset"]
        while day < DAYS:
            d = START + dt.timedelta(days=day)
            for sku in ds.skus:
                code = sku["code"]
                if sku["launch"]:
                    if code not in adopt or day < adopt[code]:
                        continue
                elif not carries[code]:
                    continue
                grams, price = sku["grams"], sku["price"]
                ev = events.get(code)
                if ev and day >= switch[code]:
                    grams = ev["grams_after"]
                    price = price * ev["price_mult"]
                in_stock = rng.random() < 0.93
                rec = {"store": store["code"], "sku": code, "visit_date": d, "in_stock": in_stock,
                       "price": None, "pack_grams": None, "facings": 0, "image_ref": ""}
                if in_stock:
                    if sku["fixed_mrp"] and not (ev and ev["kind"] in ("resize", "upsize", "price_hike") and day >= switch[code]):
                        shelf_price = price
                    else:
                        shelf_price = price * inflation(store["city"], d) * noise[code]
                        if rng.random() < 0.05:
                            shelf_price *= 0.9  # promo
                        shelf_price = round(shelf_price)
                    read = grams
                    if rng.random() < ocr_noise:  # OCR misread of the pack weight
                        read = rng.choice([grams // 10, grams * 10, grams + rng.choice([-50, 50, 100])])
                        read = max(1, read)
                    img += 1
                    rec.update(price=float(shelf_price), pack_grams=int(read),
                               facings=rng.randint(1, 6), image_ref=f"IMG{img:07d}")
                obs.append(rec)
            day += visit_every

    # Ground-truth launch speed over ALL stores (non-adopters never reach)
    gt_launch = {}
    for code, meta in launch_meta.items():
        delays = sorted(a - meta["day"] for a in truth_launch[code] if a is not None)
        n = len(truth_launch[code])

        def days_to(share):
            k = math.ceil(share * n)
            return delays[k - 1] if k <= len(delays) else None

        gt_launch[code] = {"launch_day": meta["day"], "mean_days": meta["mean_days"],
                           "days_to_25": days_to(0.25), "days_to_50": days_to(0.5)}

    ds.observations = obs
    ds.truth = {
        "pack_events": events,
        "launches": gt_launch,
        "shock": {"city": SHOCK_CITY, "month": SHOCK_MONTH},
        "city_monthly_rate": city_rate,
    }
    return ds

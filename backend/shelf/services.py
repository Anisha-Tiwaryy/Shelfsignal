"""Glue between the database and the pure detectors."""
from __future__ import annotations

import time

import pandas as pd
from django.db import transaction
from django.utils import timezone

from . import detectors
from .models import (SKU, DetectorRun, LaunchSignal, Observation, PackChangeSignal,
                     PriceIndexPoint, Store)


def load_dataset(ds, batch_size: int = 5000) -> int:
    """Bulk-load a synthetic Dataset into the database (replacing old data)."""
    with transaction.atomic():
        Observation.objects.all().delete()
        DetectorRun.objects.all().delete()
        SKU.objects.all().delete()
        Store.objects.all().delete()
        stores = Store.objects.bulk_create(
            [Store(code=s["code"], city=s["city"], channel=s["channel"]) for s in ds.stores])
        skus = SKU.objects.bulk_create(
            [SKU(code=s["code"], brand=s["brand"], category=s["category"], name=s["name"]) for s in ds.skus])
        store_id = {s.code: s.id for s in stores}
        sku_id = {s.code: s.id for s in skus}
        rows = [Observation(store_id=store_id[o["store"]], sku_id=sku_id[o["sku"]], visit_date=o["visit_date"],
                            in_stock=o["in_stock"], price=o["price"], pack_grams=o["pack_grams"],
                            facings=o["facings"], image_ref=o["image_ref"]) for o in ds.observations]
        Observation.objects.bulk_create(rows, batch_size=batch_size)
    return len(rows)


def observations_frame() -> pd.DataFrame:
    qs = Observation.objects.values_list(
        "store__code", "store__city", "sku__code", "visit_date", "in_stock", "price", "pack_grams")
    df = pd.DataFrame.from_records(
        list(qs), columns=["store", "city", "sku", "visit_date", "in_stock", "price", "pack_grams"])
    if not df.empty:
        df["price"] = df["price"].astype(float)
    return df


def execute_run(run: DetectorRun) -> DetectorRun:
    t0 = time.perf_counter()
    run.status = "running"
    run.save(update_fields=["status"])
    try:
        df = observations_frame()
        pack = detectors.detect_pack_changes(df)
        launches = detectors.detect_launches(df)
        index = detectors.price_index(df, {r["sku"] for r in launches})
        sku = {s.code: s for s in SKU.objects.all()}
        with transaction.atomic():
            PackChangeSignal.objects.bulk_create([
                PackChangeSignal(run=run, sku=sku[r["sku"]], kind=r["kind"], grams_before=r["grams_before"],
                                 grams_after=r["grams_after"], price_change_pct=r["price_change_pct"],
                                 per_gram_change_pct=r["per_gram_change_pct"], first_seen=r["first_seen"],
                                 stores_changed=r["stores_changed"], stores_carrying=r["stores_carrying"],
                                 confidence=r["confidence"]) for r in pack])
            LaunchSignal.objects.bulk_create([
                LaunchSignal(run=run, sku=sku[r["sku"]], first_seen=r["first_seen"], days_to_25=r["days_to_25"],
                             days_to_50=r["days_to_50"], reach_pct=r["reach_pct"], curve=r["curve"])
                for r in launches])
            PriceIndexPoint.objects.bulk_create([PriceIndexPoint(run=run, **r) for r in index])
        run.status = "done"
        run.observations_scanned = len(df)
    except Exception as exc:  # recorded on the run so the API can surface it
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"
    run.duration_ms = int((time.perf_counter() - t0) * 1000)
    run.finished_at = timezone.now()
    run.save()
    return run


def latest_run() -> DetectorRun | None:
    return DetectorRun.objects.filter(status="done").order_by("-id").first()

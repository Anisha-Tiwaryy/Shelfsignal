"""Data model.

Observation is one SKU on one shelf on one visit: the structured record an
image-recognition pipeline already produces (SKU id, shelf price label,
pack weight read off the pack, facings, in/out of stock). Everything
downstream is derived from these rows.
"""
from django.db import models


class Store(models.Model):
    CHANNELS = [("kirana", "Kirana"), ("modern_trade", "Modern Trade")]
    code = models.CharField(max_length=20, unique=True)
    city = models.CharField(max_length=40, db_index=True)
    channel = models.CharField(max_length=20, choices=CHANNELS)

    def __str__(self):
        return self.code


class SKU(models.Model):
    code = models.CharField(max_length=20, unique=True)
    brand = models.CharField(max_length=60)
    category = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=120)

    def __str__(self):
        return self.code


class Observation(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="observations")
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE, related_name="observations")
    visit_date = models.DateField()
    in_stock = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    pack_grams = models.PositiveIntegerField(null=True, blank=True)
    facings = models.PositiveSmallIntegerField(default=0)
    image_ref = models.CharField(max_length=40, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["sku", "store", "visit_date"]),
            models.Index(fields=["visit_date"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["store", "sku", "visit_date"], name="one_obs_per_visit"),
        ]


class DetectorRun(models.Model):
    STATUS = [("queued", "Queued"), ("running", "Running"), ("done", "Done"), ("failed", "Failed")]
    status = models.CharField(max_length=10, choices=STATUS, default="queued")
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    observations_scanned = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)


class PackChangeSignal(models.Model):
    KINDS = [("shrinkflation", "Shrinkflation"), ("resize", "Proportional resize"), ("upsize", "Upsize")]
    run = models.ForeignKey(DetectorRun, on_delete=models.CASCADE, related_name="pack_changes")
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    kind = models.CharField(max_length=15, choices=KINDS)
    grams_before = models.PositiveIntegerField()
    grams_after = models.PositiveIntegerField()
    price_change_pct = models.FloatField()
    per_gram_change_pct = models.FloatField()
    first_seen = models.DateField()
    stores_changed = models.PositiveIntegerField()
    stores_carrying = models.PositiveIntegerField()
    confidence = models.FloatField()


class LaunchSignal(models.Model):
    run = models.ForeignKey(DetectorRun, on_delete=models.CASCADE, related_name="launches")
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    first_seen = models.DateField()
    days_to_25 = models.IntegerField(null=True)
    days_to_50 = models.IntegerField(null=True)
    reach_pct = models.FloatField()
    curve = models.JSONField(default=list)  # [[day, share], ...]


class PriceIndexPoint(models.Model):
    run = models.ForeignKey(DetectorRun, on_delete=models.CASCADE, related_name="index_points")
    city = models.CharField(max_length=40)
    month = models.CharField(max_length=7)  # YYYY-MM
    pack_index = models.FloatField()
    per_gram_index = models.FloatField()
    shock = models.BooleanField(default=False)

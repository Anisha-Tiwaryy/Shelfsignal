from rest_framework import serializers

from .models import (SKU, DetectorRun, LaunchSignal, Observation, PackChangeSignal,
                     PriceIndexPoint)


class SKUSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = ["code", "brand", "category", "name"]


class ObservationSerializer(serializers.ModelSerializer):
    store = serializers.CharField(source="store.code")
    city = serializers.CharField(source="store.city")
    sku = serializers.CharField(source="sku.code")

    class Meta:
        model = Observation
        fields = ["store", "city", "sku", "visit_date", "in_stock", "price", "pack_grams", "facings", "image_ref"]


class DetectorRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectorRun
        fields = ["id", "status", "created_at", "finished_at", "observations_scanned", "duration_ms", "error"]
        read_only_fields = fields


class PackChangeSerializer(serializers.ModelSerializer):
    sku = SKUSerializer()

    class Meta:
        model = PackChangeSignal
        exclude = ["id", "run"]


class LaunchSerializer(serializers.ModelSerializer):
    sku = SKUSerializer()

    class Meta:
        model = LaunchSignal
        exclude = ["id", "run"]


class PriceIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceIndexPoint
        exclude = ["id", "run"]

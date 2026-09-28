from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import brief
from .models import SKU, DetectorRun, LaunchSignal, Observation, PackChangeSignal, PriceIndexPoint
from .serializers import (DetectorRunSerializer, LaunchSerializer, ObservationSerializer,
                          PackChangeSerializer, PriceIndexSerializer, SKUSerializer)
from .services import latest_run
from .tasks import run_detectors


class SKUList(generics.ListAPIView):
    queryset = SKU.objects.order_by("code")
    serializer_class = SKUSerializer


class ObservationList(generics.ListAPIView):
    """Raw shelf observations. Filters: ?sku=SKU003&city=Delhi&store=ST001"""
    serializer_class = ObservationSerializer

    def get_queryset(self):
        qs = Observation.objects.select_related("store", "sku").order_by("visit_date", "id")
        p = self.request.query_params
        if p.get("sku"):
            qs = qs.filter(sku__code=p["sku"])
        if p.get("city"):
            qs = qs.filter(store__city=p["city"])
        if p.get("store"):
            qs = qs.filter(store__code=p["store"])
        return qs


class DetectorRunViewSet(viewsets.ModelViewSet):
    """POST queues a background detector run (Celery); GET polls its status."""
    queryset = DetectorRun.objects.order_by("-id")
    serializer_class = DetectorRunSerializer
    http_method_names = ["get", "post"]

    def create(self, request, *args, **kwargs):
        run = DetectorRun.objects.create()
        run_detectors.delay(run.id)
        run.refresh_from_db()
        return Response(DetectorRunSerializer(run).data, status=status.HTTP_202_ACCEPTED)


def _run_or_404(request):
    run_id = request.query_params.get("run")
    run = DetectorRun.objects.filter(pk=run_id, status="done").first() if run_id else latest_run()
    return run


@api_view(["GET"])
def pack_changes(request):
    run = _run_or_404(request)
    if not run:
        return Response({"detail": "No completed detector run yet. POST /api/runs/ first."}, status=404)
    qs = PackChangeSignal.objects.filter(run=run).select_related("sku").order_by("-per_gram_change_pct")
    kind = request.query_params.get("kind")
    if kind:
        qs = qs.filter(kind=kind)
    return Response({"run": run.id, "results": PackChangeSerializer(qs, many=True).data})


@api_view(["GET"])
def launches(request):
    run = _run_or_404(request)
    if not run:
        return Response({"detail": "No completed detector run yet."}, status=404)
    qs = LaunchSignal.objects.filter(run=run).select_related("sku").order_by("days_to_50")
    return Response({"run": run.id, "results": LaunchSerializer(qs, many=True).data})


@api_view(["GET"])
def price_index(request):
    run = _run_or_404(request)
    if not run:
        return Response({"detail": "No completed detector run yet."}, status=404)
    qs = PriceIndexPoint.objects.filter(run=run).order_by("city", "month")
    if request.query_params.get("city"):
        qs = qs.filter(city=request.query_params["city"])
    return Response({"run": run.id, "results": PriceIndexSerializer(qs, many=True).data})


@api_view(["GET"])
def weekly_brief(request):
    run = _run_or_404(request)
    if not run:
        return Response({"detail": "No completed detector run yet."}, status=404)
    pack = [dict(PackChangeSerializer(p).data, sku=p.sku.code) for p in PackChangeSignal.objects.filter(run=run)]
    launch = [dict(LaunchSerializer(l).data, sku=l.sku.code)
              for l in LaunchSignal.objects.filter(run=run).order_by("days_to_50")]
    index = list(PriceIndexPoint.objects.filter(run=run).values("city", "month", "pack_index", "per_gram_index", "shock"))
    return Response({"run": run.id, **brief.build_brief(pack, launch, index)})

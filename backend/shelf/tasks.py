from celery import shared_task

from .models import DetectorRun
from .services import execute_run


@shared_task
def run_detectors(run_id: int) -> str:
    """Background job: scan all observations and rebuild the signal tables."""
    run = DetectorRun.objects.get(pk=run_id)
    return execute_run(run).status

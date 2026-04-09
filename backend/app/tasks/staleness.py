"""
Staleness detection task.

Runs every minute via Celery Beat.  For every visible service that has
`stale_after_seconds` configured, checks whether `status_updated_at` is
older than the threshold.  If it is, and the current status is not already
"unknown", the service is set to "unknown" and a StatusSnapshot is written.
"""

from datetime import datetime, timedelta

from app.extensions import celery
from app.models import Service, StatusSnapshot


@celery.task(name="app.tasks.staleness.check_stale_services")
def check_stale_services():
    now = datetime.utcnow()
    marked = 0

    for service in Service.objects(visible=True):
        threshold = service.stale_after_seconds
        if not threshold:
            continue
        if service.status == "unknown":
            continue

        last_update = service.status_updated_at or service.updated_at
        if not last_update:
            continue

        age_seconds = (now - last_update).total_seconds()
        if age_seconds >= threshold:
            service.status            = "unknown"
            service.updated_at        = now
            service.status_updated_at = now
            service.save()
            StatusSnapshot(
                service=service,
                status="unknown",
                note=f"[staleness] No status update for {int(age_seconds)}s (threshold: {threshold}s)",
            ).save()
            marked += 1

    return f"Marked {marked} stale service(s) as unknown"

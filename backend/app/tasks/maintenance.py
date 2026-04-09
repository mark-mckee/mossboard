"""
Maintenance auto-status task.

Runs every minute via Celery Beat.

- When a window with auto_status=True becomes active (starts_at <= now <= ends_at)
  and we haven't applied the status yet: set the linked service to under_maintenance
  and write a StatusSnapshot.

- When such a window ends (ends_at < now) and we had applied the status: restore the
  service to operational (unless another active auto_status window still covers it)
  and write a StatusSnapshot.
"""

from datetime import datetime

from app.extensions import celery
from app.models import Service, StatusSnapshot
from app.models.maintenance import ScheduledMaintenance


@celery.task(name="app.tasks.maintenance.check_maintenance_windows")
def check_maintenance_windows():
    now = datetime.utcnow()
    applied = 0
    restored = 0

    # ── Activate windows that just started ──────────────────────────────────
    for m in ScheduledMaintenance.objects(
        auto_status=True,
        auto_status_applied=False,
        starts_at__lte=now,
        ends_at__gte=now,
    ):
        service = m.service
        if not service:
            continue
        service.status = "under_maintenance"
        service.updated_at = now
        service.status_updated_at = now
        service.save()
        StatusSnapshot(
            service=service,
            status="under_maintenance",
            note=f"[maintenance] {m.title}",
        ).save()
        m.auto_status_applied = True
        m.save()
        applied += 1

    # ── Restore services whose window just ended ─────────────────────────────
    for m in ScheduledMaintenance.objects(
        auto_status=True,
        auto_status_applied=True,
        ends_at__lt=now,
    ):
        service = m.service
        if service and service.status == "under_maintenance":
            # Only restore if no other active auto_status window covers this service
            other_active = ScheduledMaintenance.objects(
                auto_status=True,
                starts_at__lte=now,
                ends_at__gte=now,
                service=service,
                id__ne=m.id,
            ).count()
            if other_active == 0:
                service.status = "operational"
                service.updated_at = now
                service.status_updated_at = now
                service.save()
                StatusSnapshot(
                    service=service,
                    status="operational",
                    note=f"[maintenance] {m.title} ended",
                ).save()
                restored += 1
        # Mark as done so we don't process it again
        m.auto_status_applied = False
        m.save()

    return f"Applied {applied}, restored {restored} maintenance window(s)"

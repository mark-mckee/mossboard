"""
Maintenance auto-status task.

Runs every minute via Celery Beat.

- When a window with auto_status=True becomes active (starts_at <= now <= ends_at)
  and we haven't applied the status yet: set all linked services to under_maintenance
  and write a StatusSnapshot per service.

- When such a window ends (ends_at < now) and we had applied the status: restore each
  service to operational (unless another active auto_status window still covers it)
  and write a StatusSnapshot.

- When a recurring window ends: spawn the next occurrence.
"""

import calendar
from datetime import datetime, timedelta

from app.extensions import celery
from app.models import Service, StatusSnapshot
from app.models.maintenance import ScheduledMaintenance


def _next_occurrence(m):
    """Return (new_starts_at, new_ends_at) for the next recurrence, or (None, None)."""
    duration = m.ends_at - m.starts_at
    s = m.starts_at

    if m.recurrence == "daily":
        new_starts = s + timedelta(days=1)
    elif m.recurrence == "weekly":
        new_starts = s + timedelta(weeks=1)
    elif m.recurrence == "monthly":
        month = s.month + 1
        year = s.year
        if month > 12:
            month = 1
            year += 1
        max_day = calendar.monthrange(year, month)[1]
        new_starts = s.replace(year=year, month=month, day=min(s.day, max_day))
    else:
        return None, None

    return new_starts, new_starts + duration


@celery.task(name="app.tasks.maintenance.check_maintenance_windows")
def check_maintenance_windows():
    now = datetime.utcnow()
    applied = 0
    restored = 0
    spawned = 0

    def _all_services(m):
        svcs = list(m.services or [])
        try:
            if m.service and m.service not in svcs:
                svcs.insert(0, m.service)
        except Exception:
            pass
        return svcs

    # ── Activate windows that just started ──────────────────────────────────
    for m in ScheduledMaintenance.objects(
        auto_status=True,
        auto_status_applied=False,
        starts_at__lte=now,
        ends_at__gte=now,
    ):
        for service in _all_services(m):
            try:
                service.status = "under_maintenance"
                service.updated_at = now
                service.status_updated_at = now
                service.save()
                StatusSnapshot(
                    service=service,
                    status="under_maintenance",
                    note=f"[maintenance] {m.title}",
                ).save()
                applied += 1
            except Exception:
                pass
        m.auto_status_applied = True
        m.save()

    # ── Restore services whose window just ended ─────────────────────────────
    for m in ScheduledMaintenance.objects(
        auto_status=True,
        auto_status_applied=True,
        ends_at__lt=now,
    ):
        for service in _all_services(m):
            try:
                if service.status == "under_maintenance":
                    # Only restore if no other active auto_status window still covers this service
                    other_active = ScheduledMaintenance.objects(
                        auto_status=True,
                        starts_at__lte=now,
                        ends_at__gte=now,
                        services=service,
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
            except Exception:
                pass

        # Mark as done so we don't process it again
        m.auto_status_applied = False
        m.save()

        # Spawn next recurrence
        if m.recurrence != "none":
            new_starts, new_ends = _next_occurrence(m)
            if new_starts:
                ScheduledMaintenance(
                    services=list(m.services),
                    title=m.title,
                    description=m.description,
                    starts_at=new_starts,
                    ends_at=new_ends,
                    auto_status=m.auto_status,
                    auto_status_applied=False,
                    recurrence=m.recurrence,
                    recurrence_day=m.recurrence_day,
                ).save()
                spawned += 1

    return f"Applied {applied}, restored {restored}, spawned {spawned} maintenance window(s)"

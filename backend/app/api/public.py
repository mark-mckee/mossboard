from datetime import datetime, timedelta
from apiflask import APIBlueprint
from flask import request as flask_request
from app.models import Section, Service, StatusSnapshot, Incident, ScheduledMaintenance
from app.models.settings import Settings

public_bp = APIBlueprint("public", __name__, url_prefix="/api/v1")

from flask import abort as _abort

BLOCK_MINUTES = 5   # snapshot granularity
BLOCK_COUNT   = 288 # 24 h × 60 min / 5 min


def _get_or_404(qs):
    obj = qs.first()
    if obj is None:
        _abort(404)
    return obj


STATUS_PRIORITY = {
    "major_outage": 6, "partial_outage": 5, "performance_issues": 4,
    "under_maintenance": 3, "unknown": 2, "operational": 1,
}


def worst_status(statuses):
    if not statuses:
        return "unknown"
    return max(statuses, key=lambda s: STATUS_PRIORITY.get(s, 0))


def _section_of(service):
    try:
        s = service.section
        return {"section_id": str(s.id), "section_name": s.name} if s else {}
    except Exception:
        return {}


def serialize_service(service):
    sec = _section_of(service)
    return {
        "id": str(service.id),
        "section_id":   sec.get("section_id"),
        "section_name": sec.get("section_name"),
        "name": service.name,
        "slug": service.slug,
        "description": service.description,
        "status": service.status,
        "order": service.order,
        "updated_at": service.updated_at.isoformat() + "Z" if service.updated_at else None,
    }


def serialize_section_with_services(section):
    services = Service.objects(section=section, visible=True).order_by("order")
    return {
        "id": str(section.id),
        "name": section.name,
        "slug": section.slug,
        "order": section.order,
        "services": [serialize_service(s) for s in services],
    }


@public_bp.get("/status")
def get_status():
    sections     = Section.objects(visible=True).order_by("order")
    all_services = Service.objects(visible=True)
    overall      = worst_status([s.status for s in all_services])
    cfg          = Settings.get_or_create()
    return {
        "overall_status":          overall,
        "sections":                [serialize_section_with_services(s) for s in sections],
        "site_title":              cfg.site_title or "MOSSBoard",
        "default_theme":           cfg.default_theme or "dark",
        "show_incident_timeline":  bool(cfg.show_incident_timeline),
        "incident_timeline_days":  cfg.incident_timeline_days or 7,
    }


@public_bp.get("/services/<slug>/history")
def get_service_history(slug):
    service = _get_or_404(Service.objects(slug=slug))
    now = datetime.utcnow()
    blocks = []

    for i in range(BLOCK_COUNT - 1, -1, -1):
        block_end   = now - timedelta(minutes=BLOCK_MINUTES * i)
        block_start = block_end - timedelta(minutes=BLOCK_MINUTES)
        snapshots   = StatusSnapshot.objects(
            service=service, recorded_at__gte=block_start, recorded_at__lt=block_end
        )
        blocks.append({
            "block_start": block_start.isoformat() + "Z",
            "block_end":   block_end.isoformat() + "Z",
            "status":      worst_status([sn.status for sn in snapshots]),
        })

    return {"service": serialize_service(service), "history": blocks}


@public_bp.get("/services/<slug>/incidents")
def get_service_incidents(slug):
    service = _get_or_404(Service.objects(slug=slug))
    resolved_qs    = Incident.objects(service=service, resolved_at__ne=None).order_by("-created_at")
    resolved_total = resolved_qs.count()
    return {
        "open":           [serialize_incident(i) for i in Incident.objects(service=service, resolved_at=None).order_by("-created_at")],
        "resolved":       [serialize_incident(i) for i in resolved_qs.limit(20)],
        "resolved_total": resolved_total,
    }


@public_bp.get("/services/<slug>/log")
def get_service_log(slug):
    service   = _get_or_404(Service.objects(slug=slug))
    snapshots = list(StatusSnapshot.objects(service=service).order_by("recorded_at"))

    if not snapshots:
        return {"log": [], "service": serialize_service(service)}

    periods = []
    cur_status = snapshots[0].status
    cur_start  = snapshots[0].recorded_at
    cur_note   = snapshots[0].note or ""

    for snap in snapshots[1:]:
        if snap.status != cur_status:
            delta = snap.recorded_at - cur_start
            periods.append({"status": cur_status, "started_at": cur_start.isoformat() + "Z",
                             "ended_at": snap.recorded_at.isoformat() + "Z",
                             "duration_minutes": max(1, int(delta.total_seconds() / 60)),
                             "note": cur_note})
            cur_status = snap.status
            cur_start  = snap.recorded_at
            cur_note   = snap.note or ""

    now   = datetime.utcnow()
    delta = now - cur_start
    periods.append({"status": cur_status, "started_at": cur_start.isoformat() + "Z",
                    "ended_at": None, "duration_minutes": max(1, int(delta.total_seconds() / 60)),
                    "note": cur_note})

    all_periods = list(reversed(periods))
    return {"log": all_periods[:100], "total": len(all_periods), "service": serialize_service(service)}


def _apply_no_data_behavior(buckets, behavior):
    """Adjust bucket statuses in-place according to no_data_behavior setting."""
    for b in buckets:
        if not b["has_data"] and behavior == "operational":
            b["status"] = "operational"
    return buckets


def _uptime_pct(buckets, behavior):
    """Compute uptime % from snapshot counts stored per bucket.

    Uses actual snapshot counts (not worst-status per bucket) so that a day
    with e.g. 50 % operational and 50 % performance_issues correctly produces
    50 % uptime rather than 0 %.

    Behavior modes:
      exclude     — only buckets that have data contribute to the calculation.
      unknown     — same snapshot-based math; empty buckets have no snapshots
                    so they neither add to numerator nor denominator.
      operational — empty buckets are treated as fully operational: an estimated
                    number of virtual operational snapshots is added for each
                    empty bucket (based on the average snapshot rate of the
                    buckets that do have data).
    """
    if not buckets:
        return None

    buckets_with_data = [b for b in buckets if b["has_data"]]
    total_actual       = sum(b["_total"]       for b in buckets_with_data)
    operational_actual = sum(b["_operational"] for b in buckets_with_data)

    if behavior == "operational":
        empty_count = len(buckets) - len(buckets_with_data)
        if empty_count and buckets_with_data:
            avg = total_actual / len(buckets_with_data)
            virtual = round(empty_count * avg)
        else:
            virtual = 0
        total       = total_actual + virtual
        operational = operational_actual + virtual
    else:
        # "exclude" or "unknown": snapshot-based, empty periods not counted
        total       = total_actual
        operational = operational_actual

    if total == 0:
        return None
    return round(operational / total * 100, 1)


def _strip_internal(buckets):
    """Remove internal snapshot-count fields before returning to the client."""
    for b in buckets:
        b.pop("_operational", None)
        b.pop("_total", None)


def _month_boundaries(year, month):
    """Return (start, end) naive UTC datetimes for the given calendar month."""
    start = datetime(year, month, 1)
    end   = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end


@public_bp.get("/services/<slug>/uptime")
def get_service_uptime(slug):
    service  = _get_or_404(Service.objects(slug=slug))
    behavior = Settings.get_or_create().no_data_behavior
    now = datetime.utcnow()
    days = []
    for i in range(29, -1, -1):
        day_end   = now - timedelta(days=i)
        day_start = day_end - timedelta(days=1)
        snaps     = list(StatusSnapshot.objects(service=service, recorded_at__gte=day_start, recorded_at__lt=day_end))
        statuses  = [sn.status for sn in snaps]
        days.append({
            "date":          day_start.date().isoformat(),
            "status":        worst_status(statuses),
            "has_data":      len(statuses) > 0,
            "_operational":  sum(1 for s in statuses if s == "operational"),
            "_total":        len(statuses),
        })

    _apply_no_data_behavior(days, behavior)
    uptime_pct = _uptime_pct(days, behavior)
    _strip_internal(days)
    return {"days": days, "uptime_pct": uptime_pct}


@public_bp.get("/services/<slug>/uptime12")
def get_service_uptime12(slug):
    """12-month monthly uptime summary."""
    service  = _get_or_404(Service.objects(slug=slug))
    behavior = Settings.get_or_create().no_data_behavior
    now = datetime.utcnow()
    cur_year, cur_month = now.year, now.month

    months = []
    for i in range(11, -1, -1):
        m = cur_month - i
        y = cur_year
        if m <= 0:
            m += 12
            y -= 1
        start, end = _month_boundaries(y, m)
        snaps    = list(StatusSnapshot.objects(service=service, recorded_at__gte=start, recorded_at__lt=end))
        statuses = [sn.status for sn in snaps]
        months.append({
            "year":         y,
            "month":        m,
            "date":         f"{y}-{m:02d}",
            "status":       worst_status(statuses),
            "has_data":     len(statuses) > 0,
            "_operational": sum(1 for s in statuses if s == "operational"),
            "_total":       len(statuses),
        })

    _apply_no_data_behavior(months, behavior)
    uptime_pct = _uptime_pct(months, behavior)
    _strip_internal(months)
    return {"months": months, "uptime_pct": uptime_pct}


@public_bp.get("/incidents")
def get_all_incidents():
    """Incidents within a rolling day window across all services."""
    cfg  = Settings.get_or_create()
    days = flask_request.args.get("days", type=int) or cfg.incident_timeline_days or 7
    cutoff = datetime.utcnow() - timedelta(days=days)

    open_qs     = Incident.objects(resolved_at=None, created_at__gte=cutoff).order_by("-created_at")
    resolved_qs = Incident.objects(resolved_at__ne=None, resolved_at__gte=cutoff).order_by("-resolved_at")
    return {
        "open":           [serialize_incident(i) for i in open_qs],
        "resolved":       [serialize_incident(i) for i in resolved_qs],
        "resolved_total": resolved_qs.count(),
        "days":           days,
    }


@public_bp.get("/maintenance")
def get_maintenance():
    now = datetime.utcnow()
    upcoming = ScheduledMaintenance.objects(
        ends_at__gte=now, starts_at__lte=now + timedelta(days=7)
    ).order_by("starts_at")
    return {"maintenance": [_ser_maintenance(m) for m in upcoming]}


def _ser_maintenance(m):
    sec_name = None
    try:
        if m.service and m.service.section:
            sec_name = m.service.section.name
    except Exception:
        pass
    return {
        "id":           str(m.id),
        "service_id":   str(m.service.id) if m.service else None,
        "service_name": m.service.name if m.service else None,
        "section_name": sec_name,
        "title":        m.title,
        "description":  m.description,
        "starts_at":    m.starts_at.isoformat() + "Z",
        "ends_at":      m.ends_at.isoformat() + "Z",
    }


def serialize_incident(incident):
    service      = incident.service
    section_name = None
    try:
        if service and service.section:
            section_name = service.section.name
    except Exception:
        pass
    return {
        "id":             str(incident.id),
        "title":          incident.title,
        "service_id":     str(service.id)   if service else None,
        "service_name":   service.name      if service else None,
        "service_slug":   service.slug      if service else None,
        "section_name":   section_name,
        "resolved_at":    incident.resolved_at.isoformat() + "Z" if incident.resolved_at else None,
        "created_at":     incident.created_at.isoformat() + "Z",
        "updates": [
            {"status": u.status, "message": u.message, "created_at": u.created_at.isoformat() + "Z"}
            for u in incident.updates
        ],
    }

from datetime import datetime, timedelta
from apiflask import APIBlueprint
from app.models import Section, Service, StatusSnapshot, Incident, ScheduledMaintenance

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
    sections = Section.objects(visible=True).order_by("order")
    all_services = Service.objects(visible=True)
    overall = worst_status([s.status for s in all_services])
    return {"overall_status": overall, "sections": [serialize_section_with_services(s) for s in sections]}


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


@public_bp.get("/services/<slug>/uptime")
def get_service_uptime(slug):
    service = _get_or_404(Service.objects(slug=slug))
    now = datetime.utcnow()
    days = []
    for i in range(29, -1, -1):
        day_end   = now - timedelta(days=i)
        day_start = day_end - timedelta(days=1)
        snaps     = StatusSnapshot.objects(service=service, recorded_at__gte=day_start, recorded_at__lt=day_end)
        statuses  = [sn.status for sn in snaps]
        days.append({
            "date":     day_start.date().isoformat(),
            "status":   worst_status(statuses),
            "has_data": len(statuses) > 0,
        })

    snaps_30d   = list(StatusSnapshot.objects(service=service, recorded_at__gte=now - timedelta(days=30)))
    total       = len(snaps_30d)
    operational = sum(1 for s in snaps_30d if s.status == "operational")
    uptime_pct  = round(operational / total * 100, 1) if total > 0 else None

    return {"days": days, "uptime_pct": uptime_pct}


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
        "service_id":     str(service.id) if service else None,
        "service_name":   service.name if service else None,
        "section_name":   section_name,
        "resolved_at":    incident.resolved_at.isoformat() + "Z" if incident.resolved_at else None,
        "created_at":     incident.created_at.isoformat() + "Z",
        "updates": [
            {"status": u.status, "message": u.message, "created_at": u.created_at.isoformat() + "Z"}
            for u in incident.updates
        ],
    }

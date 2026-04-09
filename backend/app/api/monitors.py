from datetime import datetime
from flask import session, abort
from apiflask import APIBlueprint
from marshmallow import Schema, fields, validate

from app.models import Service, StatusSnapshot
from app.models.monitor import Monitor, ResponseTimeThreshold, PacketLossThreshold, MONITOR_TYPES, DNS_RECORD_TYPES
from app.tasks.monitors import run_single_monitor

monitors_bp = APIBlueprint("monitors", __name__, url_prefix="/api/v1/admin/monitors")

_STATUS_VALUES = [
    "operational", "performance_issues", "partial_outage",
    "major_outage", "unknown", "under_maintenance",
]


# ── Input schemas ─────────────────────────────────────────────────────────────

class ResponseTimeThresholdSchema(Schema):
    max_ms = fields.Float(required=True)
    status = fields.String(required=True, validate=validate.OneOf(_STATUS_VALUES))

class PacketLossThresholdSchema(Schema):
    max_percent = fields.Float(required=True)
    status = fields.String(required=True, validate=validate.OneOf(_STATUS_VALUES))

class MonitorIn(Schema):
    service_id              = fields.String(required=True)
    name                    = fields.String(required=True)
    type                    = fields.String(required=True, validate=validate.OneOf(MONITOR_TYPES))
    # targets
    url                     = fields.String(load_default="")
    host                    = fields.String(load_default="")
    port                    = fields.Integer(load_default=None, allow_none=True)
    # thresholds
    response_time_thresholds = fields.List(fields.Nested(ResponseTimeThresholdSchema), load_default=[])
    packet_loss_thresholds   = fields.List(fields.Nested(PacketLossThresholdSchema), load_default=[])
    # HTTP extras
    expected_status_codes   = fields.List(fields.Integer(), load_default=[200])
    # DNS extras
    dns_record_type         = fields.String(load_default="A", validate=validate.OneOf(DNS_RECORD_TYPES))
    dns_server              = fields.String(load_default="")
    dns_expected_values     = fields.List(fields.String(), load_default=[])
    # failure
    failure_status          = fields.String(load_default="major_outage", validate=validate.OneOf(_STATUS_VALUES))
    # schedule
    interval_seconds        = fields.Integer(load_default=60)
    timeout_seconds         = fields.Integer(load_default=10)
    # confirmation period (0 = immediate)
    confirm_seconds         = fields.Integer(load_default=0)
    active                  = fields.Boolean(load_default=True)

class MonitorPatchIn(Schema):
    service_id              = fields.String()
    name                    = fields.String()
    type                    = fields.String(validate=validate.OneOf(MONITOR_TYPES))
    url                     = fields.String()
    host                    = fields.String()
    port                    = fields.Integer(allow_none=True)
    response_time_thresholds = fields.List(fields.Nested(ResponseTimeThresholdSchema))
    packet_loss_thresholds   = fields.List(fields.Nested(PacketLossThresholdSchema))
    expected_status_codes   = fields.List(fields.Integer())
    dns_record_type         = fields.String(validate=validate.OneOf(DNS_RECORD_TYPES))
    dns_server              = fields.String()
    dns_expected_values     = fields.List(fields.String())
    failure_status          = fields.String(validate=validate.OneOf(_STATUS_VALUES))
    interval_seconds        = fields.Integer()
    timeout_seconds         = fields.Integer()
    confirm_seconds         = fields.Integer()
    active                  = fields.Boolean()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(qs):
    obj = qs.first()
    if obj is None:
        abort(404)
    return obj

def require_auth():
    if not session.get("logged_in"):
        abort(401)

def _apply_thresholds(monitor, data):
    """Update embedded threshold lists from validated input data."""
    if "response_time_thresholds" in data:
        monitor.response_time_thresholds = [
            ResponseTimeThreshold(max_ms=t["max_ms"], status=t["status"])
            for t in sorted(data["response_time_thresholds"], key=lambda x: x["max_ms"])
        ]
    if "packet_loss_thresholds" in data:
        monitor.packet_loss_thresholds = [
            PacketLossThreshold(max_percent=t["max_percent"], status=t["status"])
            for t in sorted(data["packet_loss_thresholds"], key=lambda x: x["max_percent"])
        ]

def _ser_monitor(m):
    svc = m.service
    sec_name = None
    try:
        if svc and svc.section:
            sec_name = svc.section.name
    except Exception:
        pass
    return {
        "id": str(m.id),
        "name": m.name,
        "type": m.type,
        "service_id": str(svc.id) if svc else None,
        "service_name": svc.name if svc else None,
        "section_name": sec_name,
        "url": m.url,
        "host": m.host,
        "port": m.port,
        "dns_record_type": m.dns_record_type or "A",
        "dns_server": m.dns_server or "",
        "dns_expected_values": list(m.dns_expected_values or []),
        "response_time_thresholds": [
            {"max_ms": t.max_ms, "status": t.status}
            for t in m.response_time_thresholds
        ],
        "packet_loss_thresholds": [
            {"max_percent": t.max_percent, "status": t.status}
            for t in m.packet_loss_thresholds
        ],
        "expected_status_codes": list(m.expected_status_codes),
        "failure_status": m.failure_status,
        "interval_seconds": m.interval_seconds,
        "timeout_seconds": m.timeout_seconds,
        "confirm_seconds": m.confirm_seconds or 0,
        "active": m.active,
        "pending_status": m.pending_status,
        "pending_since": m.pending_since.isoformat() + "Z" if m.pending_since else None,
        "last_checked_at": m.last_checked_at.isoformat() + "Z" if m.last_checked_at else None,
        "last_result": m.last_result or {},
        "last_status": m.last_status,
        "created_at": m.created_at.isoformat() + "Z",
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

@monitors_bp.get("")
def list_monitors():
    require_auth()
    return {"monitors": [_ser_monitor(m) for m in Monitor.objects().order_by("name")]}


@monitors_bp.post("")
@monitors_bp.input(MonitorIn)
def create_monitor(json_data):
    require_auth()
    name = json_data["name"].strip()
    if not name:
        abort(400)
    service = _get_or_404(Service.objects(id=json_data["service_id"]))
    monitor = Monitor(
        service=service,
        name=name,
        type=json_data["type"],
        url=json_data["url"],
        host=json_data["host"],
        port=json_data.get("port"),
        expected_status_codes=json_data["expected_status_codes"],
        dns_record_type=json_data["dns_record_type"],
        dns_server=json_data["dns_server"],
        dns_expected_values=json_data["dns_expected_values"],
        failure_status=json_data["failure_status"],
        interval_seconds=json_data["interval_seconds"],
        timeout_seconds=json_data["timeout_seconds"],
        confirm_seconds=json_data["confirm_seconds"],
        active=json_data["active"],
    )
    _apply_thresholds(monitor, json_data)
    monitor.save()
    return _ser_monitor(monitor), 201


@monitors_bp.get("/<monitor_id>")
def get_monitor(monitor_id):
    require_auth()
    return _ser_monitor(_get_or_404(Monitor.objects(id=monitor_id)))


@monitors_bp.patch("/<monitor_id>")
@monitors_bp.input(MonitorPatchIn)
def update_monitor(monitor_id, json_data):
    require_auth()
    monitor = _get_or_404(Monitor.objects(id=monitor_id))
    if "service_id" in json_data:
        monitor.service = _get_or_404(Service.objects(id=json_data["service_id"]))
    if "name"                  in json_data: monitor.name                  = json_data["name"].strip()
    if "type"                  in json_data: monitor.type                  = json_data["type"]
    if "url"                   in json_data: monitor.url                   = json_data["url"]
    if "host"                  in json_data: monitor.host                  = json_data["host"]
    if "port"                  in json_data: monitor.port                  = json_data["port"]
    if "expected_status_codes" in json_data: monitor.expected_status_codes = json_data["expected_status_codes"]
    if "dns_record_type"       in json_data: monitor.dns_record_type       = json_data["dns_record_type"]
    if "dns_server"            in json_data: monitor.dns_server            = json_data["dns_server"]
    if "dns_expected_values"   in json_data: monitor.dns_expected_values   = json_data["dns_expected_values"]
    if "failure_status"        in json_data: monitor.failure_status        = json_data["failure_status"]
    if "interval_seconds"      in json_data: monitor.interval_seconds      = json_data["interval_seconds"]
    if "timeout_seconds"       in json_data: monitor.timeout_seconds       = json_data["timeout_seconds"]
    if "confirm_seconds"       in json_data:
        monitor.confirm_seconds = json_data["confirm_seconds"]
        # Reset pending window when confirmation period is reconfigured
        monitor.pending_status = None
        monitor.pending_since = None
    if "active"                in json_data: monitor.active                = json_data["active"]
    _apply_thresholds(monitor, json_data)
    monitor.save()
    return _ser_monitor(monitor)


@monitors_bp.delete("/<monitor_id>")
def delete_monitor(monitor_id):
    require_auth()
    _get_or_404(Monitor.objects(id=monitor_id)).delete()
    return "", 204


@monitors_bp.post("/<monitor_id>/run")
def trigger_monitor(monitor_id):
    """Manually trigger a check for this monitor (runs synchronously)."""
    require_auth()
    monitor = _get_or_404(Monitor.objects(id=monitor_id))
    run_single_monitor.delay(str(monitor.id))
    return {"ok": True, "message": "Check queued"}

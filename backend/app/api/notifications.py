"""
Admin CRUD for notification destinations and rules.
Also handles SMTP settings (extends /api/v1/admin/settings).
"""
from flask import session, abort
from apiflask import APIBlueprint
from marshmallow import Schema, fields, validate

from app.models.notification import (
    NotificationDestination, NotificationRule,
    TRIGGER_CHOICES, DEST_TYPE_CHOICES,
)
from app.models import Service

notifications_bp = APIBlueprint("notifications", __name__, url_prefix="/api/v1/admin/notifications")

_STATUS_VALUES = [
    "operational", "performance_issues", "partial_outage",
    "major_outage", "unknown", "under_maintenance",
]


def _require_auth():
    if not session.get("logged_in"):
        abort(401)


def _get_or_404(qs):
    obj = qs.first()
    if obj is None:
        abort(404)
    return obj


# ── Input schemas ─────────────────────────────────────────────────────────────

class DestinationIn(Schema):
    name   = fields.String(required=True)
    type   = fields.String(required=True, validate=validate.OneOf(DEST_TYPE_CHOICES))
    # Webhook
    url           = fields.String(load_default="")
    method        = fields.String(load_default="POST", validate=validate.OneOf(["GET", "POST", "PUT", "PATCH"]))
    headers       = fields.Dict(keys=fields.String(), values=fields.String(), load_default={})
    body_template = fields.String(load_default="")
    # Email
    email_to               = fields.String(load_default="")
    email_subject_template = fields.String(load_default="")
    email_body_template    = fields.String(load_default="")
    active = fields.Boolean(load_default=True)


class DestinationPatchIn(Schema):
    name   = fields.String()
    type   = fields.String(validate=validate.OneOf(DEST_TYPE_CHOICES))
    url           = fields.String()
    method        = fields.String(validate=validate.OneOf(["GET", "POST", "PUT", "PATCH"]))
    headers       = fields.Dict(keys=fields.String(), values=fields.String())
    body_template = fields.String()
    email_to               = fields.String()
    email_subject_template = fields.String()
    email_body_template    = fields.String()
    active = fields.Boolean()


class RuleIn(Schema):
    name           = fields.String(required=True)
    trigger        = fields.String(required=True, validate=validate.OneOf(TRIGGER_CHOICES))
    destination_id = fields.String(required=True)
    filter_from_status = fields.String(load_default="", validate=validate.OneOf([""] + _STATUS_VALUES))
    filter_to_status   = fields.String(load_default="", validate=validate.OneOf([""] + _STATUS_VALUES))
    service_ids    = fields.List(fields.String(), load_default=[])
    active         = fields.Boolean(load_default=True)


class RulePatchIn(Schema):
    name           = fields.String()
    trigger        = fields.String(validate=validate.OneOf(TRIGGER_CHOICES))
    destination_id = fields.String()
    filter_from_status = fields.String(validate=validate.OneOf([""] + _STATUS_VALUES))
    filter_to_status   = fields.String(validate=validate.OneOf([""] + _STATUS_VALUES))
    service_ids    = fields.List(fields.String())
    active         = fields.Boolean()


class SmtpIn(Schema):
    smtp_host     = fields.String()
    smtp_port     = fields.Integer()
    smtp_username = fields.String()
    smtp_password = fields.String()
    smtp_from     = fields.String()
    smtp_use_tls  = fields.Boolean()


# ── Serializers ───────────────────────────────────────────────────────────────

def _ser_dest(d):
    return {
        "id":     str(d.id),
        "name":   d.name,
        "type":   d.type,
        "url":    d.url    or "",
        "method": d.method or "POST",
        "headers":       dict(d.headers or {}),
        "body_template": d.body_template or "",
        "email_to":               d.email_to               or "",
        "email_subject_template": d.email_subject_template or "",
        "email_body_template":    d.email_body_template    or "",
        "active":     bool(d.active),
        "created_at": d.created_at.isoformat() + "Z",
    }


def _ser_rule(r):
    dest = None
    try:
        dest = {"id": str(r.destination.id), "name": r.destination.name, "type": r.destination.type}
    except Exception:
        pass
    services_info = []
    try:
        for svc in r.services:
            try:
                services_info.append({"id": str(svc.id), "name": svc.name, "slug": svc.slug})
            except Exception:
                pass
    except Exception:
        pass
    return {
        "id":          str(r.id),
        "name":        r.name,
        "trigger":     r.trigger,
        "destination": dest,
        "filter_from_status": r.filter_from_status or "",
        "filter_to_status":   r.filter_to_status   or "",
        "services":    services_info,
        "active":      bool(r.active),
        "created_at":  r.created_at.isoformat() + "Z",
    }


# ── Destinations ──────────────────────────────────────────────────────────────

@notifications_bp.get("/destinations")
def list_destinations():
    _require_auth()
    return {"destinations": [_ser_dest(d) for d in NotificationDestination.objects().order_by("name")]}


@notifications_bp.post("/destinations")
@notifications_bp.input(DestinationIn)
def create_destination(json_data):
    _require_auth()
    d = NotificationDestination(
        name=json_data["name"].strip(),
        type=json_data["type"],
        url=json_data["url"],
        method=json_data["method"],
        headers=json_data["headers"],
        body_template=json_data["body_template"],
        email_to=json_data["email_to"],
        email_subject_template=json_data["email_subject_template"],
        email_body_template=json_data["email_body_template"],
        active=json_data["active"],
    ).save()
    return _ser_dest(d), 201


@notifications_bp.patch("/destinations/<dest_id>")
@notifications_bp.input(DestinationPatchIn)
def update_destination(dest_id, json_data):
    _require_auth()
    d = _get_or_404(NotificationDestination.objects(id=dest_id))
    for f in ("name", "type", "url", "method", "headers", "body_template",
              "email_to", "email_subject_template", "email_body_template", "active"):
        if f in json_data:
            setattr(d, f, json_data[f].strip() if f == "name" else json_data[f])
    d.save()
    return _ser_dest(d)


@notifications_bp.delete("/destinations/<dest_id>")
def delete_destination(dest_id):
    _require_auth()
    _get_or_404(NotificationDestination.objects(id=dest_id)).delete()
    return "", 204


# ── Test destination ──────────────────────────────────────────────────────────

@notifications_bp.post("/destinations/<dest_id>/test")
def test_destination(dest_id):
    _require_auth()
    from app.tasks.notifications import dispatch_notification
    dest = _get_or_404(NotificationDestination.objects(id=dest_id))
    ctx = {
        "service_name":  "Test Service",
        "service_slug":  "test-service",
        "section_name":  "Test Section",
        "status":        "operational",
        "prev_status":   "major_outage",
        "title":         "Test Notification",
        "description":   "This is a test notification from MOSSBoard.",
        "starts_at":     "2026-01-01T00:00:00Z",
        "ends_at":       "2026-01-01T01:00:00Z",
        "message":       "Test notification message.",
        "monitor_name":  "Test Monitor",
        "timestamp":     "2026-01-01T00:00:00Z",
    }
    task = dispatch_notification.delay(str(dest.id), ctx)
    return {"task_id": task.id, "status": "queued"}


# ── Rules ─────────────────────────────────────────────────────────────────────

@notifications_bp.get("/rules")
def list_rules():
    _require_auth()
    result = []
    for r in NotificationRule.objects().order_by("name"):
        try:
            result.append(_ser_rule(r))
        except Exception:
            pass
    return {"rules": result}


@notifications_bp.post("/rules")
@notifications_bp.input(RuleIn)
def create_rule(json_data):
    _require_auth()
    dest = _get_or_404(NotificationDestination.objects(id=json_data["destination_id"]))
    services = [s for s in (Service.objects(id=sid).first() for sid in json_data["service_ids"]) if s]
    r = NotificationRule(
        name=json_data["name"].strip(),
        trigger=json_data["trigger"],
        destination=dest,
        filter_from_status=json_data["filter_from_status"],
        filter_to_status=json_data["filter_to_status"],
        services=services,
        active=json_data["active"],
    ).save()
    return _ser_rule(r), 201


@notifications_bp.patch("/rules/<rule_id>")
@notifications_bp.input(RulePatchIn)
def update_rule(rule_id, json_data):
    _require_auth()
    r = _get_or_404(NotificationRule.objects(id=rule_id))
    if "name"    in json_data: r.name    = json_data["name"].strip()
    if "trigger" in json_data: r.trigger = json_data["trigger"]
    if "active"  in json_data: r.active  = json_data["active"]
    if "filter_from_status" in json_data: r.filter_from_status = json_data["filter_from_status"]
    if "filter_to_status"   in json_data: r.filter_to_status   = json_data["filter_to_status"]
    if "destination_id" in json_data:
        r.destination = _get_or_404(NotificationDestination.objects(id=json_data["destination_id"]))
    if "service_ids" in json_data:
        r.services = [s for s in (Service.objects(id=sid).first() for sid in json_data["service_ids"]) if s]
    r.save()
    return _ser_rule(r)


@notifications_bp.delete("/rules/<rule_id>")
def delete_rule(rule_id):
    _require_auth()
    _get_or_404(NotificationRule.objects(id=rule_id)).delete()
    return "", 204


# ── SMTP settings ─────────────────────────────────────────────────────────────

@notifications_bp.get("/smtp")
def get_smtp():
    _require_auth()
    from app.models.settings import Settings
    s = Settings.get_or_create()
    return {
        "smtp_host":     s.smtp_host     or "",
        "smtp_port":     s.smtp_port     or 587,
        "smtp_username": s.smtp_username or "",
        "smtp_from":     s.smtp_from     or "",
        "smtp_use_tls":  bool(s.smtp_use_tls),
        # Never return password
    }


@notifications_bp.patch("/smtp")
@notifications_bp.input(SmtpIn)
def update_smtp(json_data):
    _require_auth()
    from app.models.settings import Settings
    s = Settings.get_or_create()
    if "smtp_host"     in json_data: s.smtp_host     = json_data["smtp_host"].strip()
    if "smtp_port"     in json_data: s.smtp_port     = json_data["smtp_port"]
    if "smtp_username" in json_data: s.smtp_username = json_data["smtp_username"].strip()
    if "smtp_password" in json_data: s.smtp_password = json_data["smtp_password"]
    if "smtp_from"     in json_data: s.smtp_from     = json_data["smtp_from"].strip()
    if "smtp_use_tls"  in json_data: s.smtp_use_tls  = json_data["smtp_use_tls"]
    s.save()
    return get_smtp()

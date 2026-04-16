from datetime import datetime
from flask import session, current_app, abort
from apiflask import APIBlueprint
from marshmallow import Schema, fields, validate
from slugify import slugify

import bcrypt as _bcrypt
from app.models import Section, Service, Incident, IncidentUpdate, APIToken, ScheduledMaintenance, User, StatusSnapshot, Metric
from app.api.public import serialize_incident

admin_bp = APIBlueprint("admin", __name__, url_prefix="/api/v1/admin")

_STATUS_VALUES = ["operational", "performance_issues", "partial_outage",
                  "major_outage", "unknown", "under_maintenance"]
_INC_STATUS    = ["investigating", "identified", "monitoring", "resolved"]
_ROLES         = ["admin", "viewer"]


# ── Input schemas ─────────────────────────────────────────────────────────────

class LoginIn(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)

class SectionIn(Schema):
    name    = fields.String(required=True)
    order   = fields.Integer(load_default=0)
    visible = fields.Boolean(load_default=True)

class SectionPatchIn(Schema):
    name    = fields.String()
    order   = fields.Integer()
    visible = fields.Boolean()

class ServiceIn(Schema):
    section_id         = fields.String(required=True, metadata={"description": "Section ID"})
    name               = fields.String(required=True)
    description        = fields.String(load_default="")
    status             = fields.String(load_default="unknown", validate=validate.OneOf(_STATUS_VALUES))
    order              = fields.Integer(load_default=0)
    visible            = fields.Boolean(load_default=True)
    note               = fields.String(load_default="", metadata={"description": "Optional reason for initial status"})
    stale_after_seconds = fields.Integer(load_default=None, allow_none=True,
                                         metadata={"description": "Set status to unknown after this many seconds without an update. null = disabled."})

class ServicePatchIn(Schema):
    section_id         = fields.String(metadata={"description": "Move to a different section"})
    name               = fields.String()
    description        = fields.String()
    status             = fields.String(validate=validate.OneOf(_STATUS_VALUES))
    note               = fields.String(load_default="", metadata={"description": "Optional reason for status change"})
    order              = fields.Integer()
    visible            = fields.Boolean()
    stale_after_seconds = fields.Integer(allow_none=True,
                                         metadata={"description": "Set status to unknown after this many seconds without an update. null = disabled."})

class IncidentIn(Schema):
    service_id = fields.String(required=True, metadata={"description": "Service ID"})
    title      = fields.String(required=True)
    status     = fields.String(load_default="investigating", validate=validate.OneOf(_INC_STATUS))
    message    = fields.String(required=True, metadata={"description": "Initial update message"})

class IncidentUpdateIn(Schema):
    status  = fields.String(required=True, validate=validate.OneOf(_INC_STATUS))
    message = fields.String(required=True)

class IncidentPatchIn(Schema):
    title    = fields.String()
    resolved = fields.Boolean(load_default=False, metadata={"description": "Set true to mark resolved"})

class MaintenanceIn(Schema):
    service_id  = fields.String(required=True, metadata={"description": "Service ID"})
    title       = fields.String(required=True)
    description = fields.String(load_default="")
    starts_at   = fields.String(required=True, metadata={"description": "ISO 8601 datetime"})
    ends_at     = fields.String(required=True, metadata={"description": "ISO 8601 datetime"})
    auto_status = fields.Boolean(load_default=False, metadata={"description": "Auto-set service to under_maintenance during window"})

class TokenIn(Schema):
    name                  = fields.String(required=True)
    allow_service_updates = fields.Boolean(load_default=True)
    service_ids           = fields.List(fields.String(), load_default=[],
                                        metadata={"description": "Service IDs; empty = all (when allow_service_updates is true)"})
    allow_metric_pushes   = fields.Boolean(load_default=True)
    metric_ids            = fields.List(fields.String(), load_default=[],
                                        metadata={"description": "Metric IDs; empty = all (when allow_metric_pushes is true)"})

class TokenPatchIn(Schema):
    active = fields.Boolean(required=True)

class UserIn(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)
    role     = fields.String(load_default="admin", validate=validate.OneOf(_ROLES))

class UserPatchIn(Schema):
    role     = fields.String(validate=validate.OneOf(_ROLES))
    active   = fields.Boolean()
    password = fields.String(metadata={"description": "Leave empty to keep current password"})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(qs):
    obj = qs.first()
    if obj is None:
        abort(404)
    return obj

def require_auth():
    if not session.get("logged_in"):
        abort(401)


# ── Auth ─────────────────────────────────────────────────────────────────────

@admin_bp.post("/login")
@admin_bp.input(LoginIn)
def login(json_data):
    username = json_data["username"]
    password = json_data["password"]

    user = User.objects(username=username, active=True).first()
    if user and _bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        session["logged_in"] = True
        session["username"]  = username
        session["role"]      = user.role
        user.last_login = datetime.utcnow()
        user.save()
        return {"ok": True, "role": user.role}

    if (username == current_app.config["ADMIN_USERNAME"]
            and password == current_app.config["ADMIN_PASSWORD"]):
        session["logged_in"] = True
        session["username"]  = username
        session["role"]      = "admin"
        return {"ok": True, "role": "admin"}

    abort(401)


@admin_bp.post("/logout")
def logout():
    session.pop("logged_in", None)
    return {"ok": True}


@admin_bp.get("/me")
def me():
    if session.get("logged_in"):
        return {"authenticated": True, "username": session.get("username", "admin"), "role": session.get("role", "admin")}
    return {"authenticated": False}


# ── Sections ─────────────────────────────────────────────────────────────────

@admin_bp.get("/sections")
def list_sections():
    require_auth()
    return {"sections": [_ser_section(s) for s in Section.objects().order_by("order")]}


@admin_bp.post("/sections")
@admin_bp.input(SectionIn)
def create_section(json_data):
    require_auth()
    name = json_data["name"].strip()
    if not name:
        abort(400)
    section = Section(name=name, slug=_unique_slug(name, Section),
                      order=json_data["order"], visible=json_data["visible"]).save()
    return _ser_section(section), 201


@admin_bp.get("/sections/<section_id>")
def get_section(section_id):
    require_auth()
    return _ser_section(_get_or_404(Section.objects(id=section_id)))


@admin_bp.patch("/sections/<section_id>")
@admin_bp.input(SectionPatchIn)
def update_section(section_id, json_data):
    require_auth()
    section = _get_or_404(Section.objects(id=section_id))
    if "name"    in json_data: section.name    = json_data["name"].strip()
    if "order"   in json_data: section.order   = json_data["order"]
    if "visible" in json_data: section.visible = json_data["visible"]
    section.save()
    return _ser_section(section)


@admin_bp.delete("/sections/<section_id>")
def delete_section(section_id):
    require_auth()
    _get_or_404(Section.objects(id=section_id)).delete()
    return "", 204


# ── Services ──────────────────────────────────────────────────────────────────

@admin_bp.get("/services")
def list_services():
    require_auth()
    return {"services": [_ser_service(s) for s in Service.objects().order_by("order")]}


@admin_bp.post("/services")
@admin_bp.input(ServiceIn)
def create_service(json_data):
    require_auth()
    name = json_data["name"].strip()
    if not name:
        abort(400)
    section = _get_or_404(Section.objects(id=json_data["section_id"]))
    service = Service(
        section=section, name=name, slug=_unique_slug(name, Service),
        description=json_data["description"], status=json_data["status"],
        order=json_data["order"], visible=json_data["visible"],
        stale_after_seconds=json_data.get("stale_after_seconds"),
    ).save()
    return _ser_service(service), 201


@admin_bp.get("/services/<service_id>")
def get_service(service_id):
    require_auth()
    return _ser_service(_get_or_404(Service.objects(id=service_id)))


@admin_bp.patch("/services/<service_id>")
@admin_bp.input(ServicePatchIn)
def update_service(service_id, json_data):
    require_auth()
    service = _get_or_404(Service.objects(id=service_id))
    if "section_id"  in json_data:
        service.section = _get_or_404(Section.objects(id=json_data["section_id"]))
    if "name"        in json_data: service.name        = json_data["name"].strip()
    if "description" in json_data: service.description = json_data["description"]
    if "order"       in json_data: service.order       = json_data["order"]
    if "visible"     in json_data: service.visible     = json_data["visible"]
    if "stale_after_seconds" in json_data: service.stale_after_seconds = json_data["stale_after_seconds"]
    status_changed = "status" in json_data and json_data["status"] != service.status
    if "status" in json_data:
        service.status = json_data["status"]
        service.status_updated_at = datetime.utcnow()
    service.updated_at = datetime.utcnow()
    service.save()
    if status_changed:
        StatusSnapshot(service=service, status=service.status,
                       note=(json_data.get("note") or "").strip()).save()
    return _ser_service(service)


@admin_bp.delete("/services/<service_id>")
def delete_service(service_id):
    require_auth()
    _get_or_404(Service.objects(id=service_id)).delete()
    return "", 204


# ── Incidents ─────────────────────────────────────────────────────────────────

@admin_bp.get("/incidents")
def list_incidents():
    require_auth()
    return {"incidents": [serialize_incident(i) for i in Incident.objects().order_by("-created_at")]}


@admin_bp.post("/incidents")
@admin_bp.input(IncidentIn)
def create_incident(json_data):
    require_auth()
    service = _get_or_404(Service.objects(id=json_data["service_id"]))
    update  = IncidentUpdate(status=json_data["status"], message=json_data["message"].strip())
    incident = Incident(service=service, title=json_data["title"].strip(), updates=[update]).save()
    return serialize_incident(incident), 201


@admin_bp.post("/incidents/<incident_id>/updates")
@admin_bp.input(IncidentUpdateIn)
def add_incident_update(incident_id, json_data):
    require_auth()
    incident = _get_or_404(Incident.objects(id=incident_id))
    update = IncidentUpdate(status=json_data["status"], message=json_data["message"].strip())
    incident.updates.append(update)
    if json_data["status"] == "resolved" and not incident.resolved_at:
        incident.resolved_at = datetime.utcnow()
    incident.save()
    return serialize_incident(incident)


@admin_bp.patch("/incidents/<incident_id>")
@admin_bp.input(IncidentPatchIn)
def update_incident(incident_id, json_data):
    require_auth()
    incident = _get_or_404(Incident.objects(id=incident_id))
    if "title" in json_data: incident.title = json_data["title"].strip()
    if json_data.get("resolved") and not incident.resolved_at:
        incident.resolved_at = datetime.utcnow()
    incident.save()
    return serialize_incident(incident)


# ── Tokens ────────────────────────────────────────────────────────────────────

@admin_bp.get("/tokens")
def list_tokens():
    require_auth()
    return {"tokens": [_ser_token(t) for t in APIToken.objects().order_by("-created_at")]}


@admin_bp.post("/tokens")
@admin_bp.input(TokenIn)
def create_token(json_data):
    require_auth()
    import secrets, bcrypt
    name = json_data["name"].strip()
    if not name:
        abort(400)
    raw_token    = secrets.token_hex(32)
    token_prefix = raw_token[:8]
    token_hash   = bcrypt.hashpw(raw_token.encode(), bcrypt.gensalt()).decode()
    services = [s for s in (Service.objects(id=sid).first() for sid in json_data["service_ids"]) if s]
    metrics  = [m for m in (Metric.objects(id=mid).first()  for mid in json_data["metric_ids"])  if m]
    token = APIToken(
        name=name, token_hash=token_hash, token_prefix=token_prefix,
        allow_service_updates=json_data["allow_service_updates"],
        services=services,
        allow_metric_pushes=json_data["allow_metric_pushes"],
        metrics=metrics,
    ).save()
    return {"id": str(token.id), "name": token.name, "token": raw_token,
            "token_prefix": token.token_prefix,
            "allow_service_updates": token.allow_service_updates,
            "service_ids": [str(s.id) for s in token.services],
            "allow_metric_pushes": token.allow_metric_pushes,
            "metric_ids":  [str(m.id) for m in token.metrics],
            "active": token.active,
            "created_at": token.created_at.isoformat() + "Z"}, 201


@admin_bp.patch("/tokens/<token_id>")
@admin_bp.input(TokenPatchIn)
def toggle_token(token_id, json_data):
    require_auth()
    token = _get_or_404(APIToken.objects(id=token_id))
    token.active = json_data["active"]
    token.save()
    return _ser_token(token)


@admin_bp.delete("/tokens/<token_id>")
def delete_token(token_id):
    require_auth()
    _get_or_404(APIToken.objects(id=token_id)).delete()
    return "", 204


# ── Users ─────────────────────────────────────────────────────────────────────

@admin_bp.get("/users")
def list_users():
    require_auth()
    return {"users": [_ser_user(u) for u in User.objects().order_by("username")]}


@admin_bp.post("/users")
@admin_bp.input(UserIn)
def create_user(json_data):
    require_auth()
    username = json_data["username"].strip()
    password = json_data["password"].strip()
    if not username or not password:
        abort(400)
    if User.objects(username=username).first():
        return {"error": "Username already exists"}, 409
    pw_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    user = User(username=username, password_hash=pw_hash, role=json_data["role"]).save()
    return _ser_user(user), 201


@admin_bp.patch("/users/<user_id>")
@admin_bp.input(UserPatchIn)
def update_user(user_id, json_data):
    require_auth()
    user = _get_or_404(User.objects(id=user_id))
    if "role"     in json_data: user.role   = json_data["role"]
    if "active"   in json_data: user.active = json_data["active"]
    if json_data.get("password"):
        user.password_hash = _bcrypt.hashpw(json_data["password"].encode(), _bcrypt.gensalt()).decode()
    user.save()
    return _ser_user(user)


@admin_bp.delete("/users/<user_id>")
def delete_user(user_id):
    require_auth()
    user = _get_or_404(User.objects(id=user_id))
    if user.role == "admin" and User.objects(role="admin", active=True).count() <= 1:
        return {"error": "Cannot delete the last admin user"}, 409
    user.delete()
    return "", 204


# ── Scheduled Maintenance ─────────────────────────────────────────────────────

@admin_bp.get("/maintenance")
def list_maintenance():
    require_auth()
    return {"maintenance": [_ser_maintenance(m) for m in ScheduledMaintenance.objects().order_by("starts_at")]}


@admin_bp.post("/maintenance")
@admin_bp.input(MaintenanceIn)
def create_maintenance(json_data):
    require_auth()
    service = _get_or_404(Service.objects(id=json_data["service_id"]))
    m = ScheduledMaintenance(
        service=service,
        title=json_data["title"].strip(),
        description=json_data["description"],
        starts_at=datetime.fromisoformat(json_data["starts_at"].replace("Z", "+00:00")).replace(tzinfo=None),
        ends_at=datetime.fromisoformat(json_data["ends_at"].replace("Z", "+00:00")).replace(tzinfo=None),
        auto_status=json_data["auto_status"],
    ).save()
    return _ser_maintenance(m), 201


@admin_bp.delete("/maintenance/<maintenance_id>")
def delete_maintenance(maintenance_id):
    require_auth()
    _get_or_404(ScheduledMaintenance.objects(id=maintenance_id)).delete()
    return "", 204


# ── Serializers ───────────────────────────────────────────────────────────────

def _unique_slug(name, model_class):
    base = slugify(name)
    slug, counter = base, 1
    while model_class.objects(slug=slug).first():
        slug = f"{base}-{counter}"; counter += 1
    return slug

def _ser_section(s):
    return {"id": str(s.id), "name": s.name, "slug": s.slug, "order": s.order,
            "visible": s.visible, "created_at": s.created_at.isoformat() + "Z"}

def _ser_service(s):
    sec = s.section
    return {"id": str(s.id), "section_id": str(sec.id) if sec else None,
            "section_name": sec.name if sec else None,
            "name": s.name, "slug": s.slug, "description": s.description,
            "status": s.status, "order": s.order, "visible": s.visible,
            "stale_after_seconds": s.stale_after_seconds,
            "status_updated_at": s.status_updated_at.isoformat() + "Z" if s.status_updated_at else None,
            "created_at": s.created_at.isoformat() + "Z",
            "updated_at": s.updated_at.isoformat() + "Z"}

def _ser_token(t):
    def _svc_info(svc):
        sec_name = None
        try:
            if svc.section: sec_name = svc.section.name
        except Exception: pass
        return {"id": str(svc.id), "name": svc.name, "section_name": sec_name}
    def _met_info(m):
        return {"id": str(m.id), "name": m.name, "service_name": m.service.name if m.service else None}
    return {"id": str(t.id), "name": t.name, "token_prefix": t.token_prefix,
            "allow_service_updates": bool(t.allow_service_updates if t.allow_service_updates is not None else True),
            "service_ids":   [str(s.id) for s in t.services],
            "services_info": [_svc_info(s) for s in t.services],
            "allow_metric_pushes": bool(t.allow_metric_pushes if t.allow_metric_pushes is not None else True),
            "metric_ids":    [str(m.id) for m in t.metrics],
            "metrics_info":  [_met_info(m) for m in t.metrics],
            "active": t.active, "created_at": t.created_at.isoformat() + "Z",
            "last_used": t.last_used.isoformat() + "Z" if t.last_used else None}

def _ser_maintenance(m):
    sec_name = None
    try:
        if m.service and m.service.section: sec_name = m.service.section.name
    except Exception: pass
    return {"id": str(m.id), "service_id": str(m.service.id) if m.service else None,
            "service_name": m.service.name if m.service else None, "section_name": sec_name,
            "title": m.title, "description": m.description,
            "starts_at": m.starts_at.isoformat() + "Z", "ends_at": m.ends_at.isoformat() + "Z",
            "auto_status": m.auto_status or False,
            "created_at": m.created_at.isoformat() + "Z"}

def _ser_user(u):
    return {"id": str(u.id), "username": u.username, "role": u.role, "active": u.active,
            "created_at": u.created_at.isoformat() + "Z",
            "last_login": u.last_login.isoformat() + "Z" if u.last_login else None}

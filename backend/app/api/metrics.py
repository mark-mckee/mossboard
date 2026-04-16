from datetime import datetime, timedelta
from flask import request, session, abort
from apiflask import APIBlueprint
from marshmallow import Schema, fields as mf, validate
import bcrypt

from app.models.metric  import Metric, MetricPoint, VIEW_CHOICES, TYPE_CHOICES
from app.models.service import Service
from app.models.token   import APIToken

metrics_bp = APIBlueprint("metrics", __name__, url_prefix="/api/v1")


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(qs):
    obj = qs.first()
    if obj is None:
        abort(404)
    return obj


def _require_session():
    if not session.get("logged_in"):
        abort(401)


def _view_cutoff(view):
    now = datetime.utcnow()
    return {
        "last_hour": now - timedelta(hours=1),
        "today":     now.replace(hour=0, minute=0, second=0, microsecond=0),
        "week":      now - timedelta(days=7),
        "month":     now - timedelta(days=30),
    }.get(view, now - timedelta(hours=1))


def _compute_current(m):
    if m.metric_type == "last":
        last = MetricPoint.objects(metric=m).order_by("-timestamp").first()
        if last is None:
            return m.default_value
        return round(last.value, m.places)
    cutoff = _view_cutoff(m.default_view)
    points = list(MetricPoint.objects(metric=m, timestamp__gte=cutoff))
    if not points:
        return m.default_value
    vals = [p.value for p in points]
    if m.metric_type == "sum":
        result = sum(vals)
    else:
        result = sum(vals) / len(vals)
    return round(result, m.places)


def _ser_metric(m, include_current=False):
    svc = m.service
    out = {
        "id":            str(m.id),
        "service_id":    str(svc.id) if svc else None,
        "service_name":  svc.name    if svc else None,
        "service_slug":  svc.slug    if svc else None,
        "name":          m.name,
        "suffix":        m.suffix        or "",
        "description":   m.description   or "",
        "default_view":  m.default_view,
        "default_value": m.default_value,
        "display_chart": bool(m.display_chart),
        "places":        m.places,
        "metric_type":   m.metric_type,
        "threshold":     m.threshold,
        "visible":       bool(m.visible),
        "created_at":    m.created_at.isoformat() + "Z",
    }
    if include_current:
        out["current_value"] = _compute_current(m)
    return out


def _token_auth():
    """Validate Bearer token; return the APIToken document or abort 401."""
    hdr = request.headers.get("Authorization", "")
    if not hdr.startswith("Bearer "):
        abort(401)
    raw = hdr[7:]
    for tok in APIToken.objects(active=True):
        if bcrypt.checkpw(raw.encode(), tok.token_hash.encode()):
            tok.update(last_used=datetime.utcnow())
            return tok
    abort(401)


# ── schemas ───────────────────────────────────────────────────────────────────

class MetricIn(Schema):
    service_id    = mf.String(required=True)
    name          = mf.String(required=True)
    suffix        = mf.String(load_default="")
    description   = mf.String(load_default="")
    default_view  = mf.String(validate=validate.OneOf(VIEW_CHOICES), load_default="last_hour")
    default_value = mf.Float(load_default=0)
    display_chart = mf.Boolean(load_default=True)
    places        = mf.Integer(validate=validate.Range(min=0, max=10), load_default=0)
    metric_type   = mf.String(validate=validate.OneOf(TYPE_CHOICES), load_default="average")
    threshold     = mf.Integer(validate=validate.Range(min=0), load_default=0)
    visible       = mf.Boolean(load_default=True)


class MetricPatchIn(Schema):
    service_id    = mf.String()
    name          = mf.String()
    suffix        = mf.String()
    description   = mf.String()
    default_view  = mf.String(validate=validate.OneOf(VIEW_CHOICES))
    default_value = mf.Float()
    display_chart = mf.Boolean()
    places        = mf.Integer(validate=validate.Range(min=0, max=10))
    metric_type   = mf.String(validate=validate.OneOf(TYPE_CHOICES))
    threshold     = mf.Integer(validate=validate.Range(min=0))
    visible       = mf.Boolean()


class PointIn(Schema):
    value     = mf.Float(required=True)
    timestamp = mf.DateTime(load_default=None)


# ── admin CRUD ────────────────────────────────────────────────────────────────

@metrics_bp.get("/admin/metrics")
def admin_list_metrics():
    _require_session()
    return {"metrics": [_ser_metric(m, include_current=True)
                        for m in Metric.objects.order_by("name")]}


@metrics_bp.post("/admin/metrics")
@metrics_bp.input(MetricIn)
def admin_create_metric(json_data):
    _require_session()
    svc = _get_or_404(Service.objects(id=json_data["service_id"]))
    m = Metric(
        service=svc,
        name=json_data["name"],
        suffix=json_data["suffix"],
        description=json_data["description"],
        default_view=json_data["default_view"],
        default_value=json_data["default_value"],
        display_chart=json_data["display_chart"],
        places=json_data["places"],
        metric_type=json_data["metric_type"],
        threshold=json_data["threshold"],
        visible=json_data["visible"],
    )
    m.save()
    return _ser_metric(m, include_current=True), 201


@metrics_bp.get("/admin/metrics/<metric_id>")
def admin_get_metric(metric_id):
    _require_session()
    return _ser_metric(_get_or_404(Metric.objects(id=metric_id)), include_current=True)


@metrics_bp.patch("/admin/metrics/<metric_id>")
@metrics_bp.input(MetricPatchIn)
def admin_update_metric(metric_id, json_data):
    _require_session()
    m = _get_or_404(Metric.objects(id=metric_id))
    if "service_id"    in json_data: m.service       = _get_or_404(Service.objects(id=json_data["service_id"]))
    if "name"          in json_data: m.name          = json_data["name"]
    if "suffix"        in json_data: m.suffix        = json_data["suffix"]
    if "description"   in json_data: m.description   = json_data["description"]
    if "default_view"  in json_data: m.default_view  = json_data["default_view"]
    if "default_value" in json_data: m.default_value = json_data["default_value"]
    if "display_chart" in json_data: m.display_chart = json_data["display_chart"]
    if "places"        in json_data: m.places        = json_data["places"]
    if "metric_type"   in json_data: m.metric_type   = json_data["metric_type"]
    if "threshold"     in json_data: m.threshold     = json_data["threshold"]
    if "visible"       in json_data: m.visible       = json_data["visible"]
    m.save()
    return _ser_metric(m, include_current=True)


@metrics_bp.delete("/admin/metrics/<metric_id>")
def admin_delete_metric(metric_id):
    _require_session()
    m = _get_or_404(Metric.objects(id=metric_id))
    MetricPoint.objects(metric=m).delete()
    m.delete()
    return "", 204


# ── public read ───────────────────────────────────────────────────────────────

@metrics_bp.get("/metrics")
def list_metrics():
    """List all visible metrics with current value. Optional ?service_slug= to filter by service."""
    qs = Metric.objects(visible=True)
    slug = request.args.get("service_slug")
    if slug:
        svc = Service.objects(slug=slug).first()
        qs  = qs.filter(service=svc) if svc else qs.none()
    return {"metrics": [_ser_metric(m, include_current=True) for m in qs.order_by("name")]}


@metrics_bp.get("/metrics/<metric_id>/points")
def get_metric_points(metric_id):
    """Return data points for chart rendering."""
    m    = _get_or_404(Metric.objects(id=metric_id, visible=True))
    view = request.args.get("view", m.default_view)
    if view not in VIEW_CHOICES:
        view = m.default_view
    cutoff = _view_cutoff(view)
    points = list(MetricPoint.objects(metric=m, timestamp__gte=cutoff).order_by("timestamp"))
    return {
        "metric":        _ser_metric(m),
        "view":          view,
        "current_value": _compute_current(m),
        "points": [
            {"value": p.value, "timestamp": p.timestamp.isoformat() + "Z"}
            for p in points
        ],
    }


# ── token push ────────────────────────────────────────────────────────────────

@metrics_bp.post("/metrics/<metric_id>/points")
@metrics_bp.input(PointIn)
@metrics_bp.doc(security=[{"BearerAuth": []}])
def push_metric_point(metric_id, json_data):
    """Push a data point to a metric (Bearer token auth)."""
    tok = _token_auth()
    m   = _get_or_404(Metric.objects(id=metric_id))

    # Service-scoped token: verify metric's service is in the allowed list
    if tok.services and m.service not in tok.services:
        abort(403)

    # Metric-scoped token: verify this exact metric is in the allowed list
    if tok.metrics and m not in tok.metrics:
        abort(403)

    ts    = json_data.get("timestamp") or datetime.utcnow()
    value = json_data["value"]

    # Threshold: within the window update the last point instead of creating a new one
    if m.threshold > 0:
        last = MetricPoint.objects(metric=m).order_by("-timestamp").first()
        if last and (datetime.utcnow() - last.timestamp).total_seconds() < m.threshold:
            if m.metric_type == "sum":
                last.value  += value
            else:                                       # running average
                last.value   = (last.value * last.count + value) / (last.count + 1)
                last.count  += 1
            last.timestamp = ts
            last.save()
            return {
                "point":   {"value": last.value, "timestamp": last.timestamp.isoformat() + "Z"},
                "updated": True,
            }

    point = MetricPoint(metric=m, value=value, timestamp=ts)
    point.save()
    return {
        "point":   {"value": point.value, "timestamp": point.timestamp.isoformat() + "Z"},
        "updated": False,
    }, 201

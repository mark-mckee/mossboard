from datetime import datetime
from flask import abort
from apiflask import APIBlueprint
from marshmallow import Schema, fields, validate
import bcrypt

from app.models import Service, APIToken, StatusSnapshot

token_bp = APIBlueprint("token_auth", __name__, url_prefix="/api/v1")

_STATUS_VALUES = [
    "operational", "performance_issues", "partial_outage",
    "major_outage", "unknown", "under_maintenance",
]


class StatusUpdateIn(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf(_STATUS_VALUES),
        metadata={"description": "New status value for the service"},
    )
    note = fields.String(
        load_default="",
        metadata={"description": "Optional reason for the status change (shown in the status log)"},
    )


def _get_or_404(qs):
    obj = qs.first()
    if obj is None:
        abort(404)
    return obj


def _get_token_from_header():
    from flask import request
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth[7:]


def _apply_status_update(service, json_data, raw_token):
    """Shared logic for both status update routes."""
    matched_token = None
    for api_token in APIToken.objects(active=True):
        if bcrypt.checkpw(raw_token.encode(), api_token.token_hash.encode()):
            matched_token = api_token
            break

    if not matched_token:
        abort(401)

    if matched_token.services:
        service_ids = [str(s.id) for s in matched_token.services]
        if str(service.id) not in service_ids:
            abort(403)

    new_status = json_data["status"]
    note       = (json_data.get("note") or "").strip()
    old_status = service.status

    service.status            = new_status
    service.updated_at        = datetime.utcnow()
    service.status_updated_at = datetime.utcnow()
    service.save()

    if new_status != old_status:
        StatusSnapshot(service=service, status=new_status, note=note).save()

    matched_token.last_used = datetime.utcnow()
    matched_token.save()

    return {
        "id":         str(service.id),
        "slug":       service.slug,
        "status":     service.status,
        "updated_at": service.updated_at.isoformat() + "Z",
    }


@token_bp.patch("/services/<slug>/status")
@token_bp.doc(
    summary="Update service status (by slug)",
    description=(
        "Set the operational status of a service via API token using the service **slug**. "
        "Generates an immediate status snapshot visible in the service log. "
        "Authenticate using **Authorize → BearerAuth** at the top of the page."
    ),
    security=[{"BearerAuth": []}],
)
@token_bp.input(StatusUpdateIn)
def set_service_status_by_slug(slug, json_data):
    raw_token = _get_token_from_header()
    if not raw_token:
        abort(401)
    service = _get_or_404(Service.objects(slug=slug))
    return _apply_status_update(service, json_data, raw_token)


@token_bp.patch("/services/id/<service_id>/status")
@token_bp.doc(
    summary="Update service status (by ID)",
    description=(
        "Set the operational status of a service via API token using the service **ID**. "
        "Generates an immediate status snapshot visible in the service log. "
        "Authenticate using **Authorize → BearerAuth** at the top of the page."
    ),
    security=[{"BearerAuth": []}],
)
@token_bp.input(StatusUpdateIn)
def set_service_status_by_id(service_id, json_data):
    raw_token = _get_token_from_header()
    if not raw_token:
        abort(401)
    service = _get_or_404(Service.objects(id=service_id))
    return _apply_status_update(service, json_data, raw_token)

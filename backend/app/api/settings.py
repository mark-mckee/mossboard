from flask import session, abort
from apiflask import APIBlueprint
from marshmallow import Schema, fields, validate

from app.models.settings import Settings, NO_DATA_BEHAVIORS

settings_bp = APIBlueprint("settings", __name__, url_prefix="/api/v1/admin/settings")


class SettingsPatchIn(Schema):
    no_data_behavior = fields.String(required=True, validate=validate.OneOf(NO_DATA_BEHAVIORS))


def _require_auth():
    if not session.get("logged_in"):
        abort(401)


def _serialize(s):
    return {"no_data_behavior": s.no_data_behavior}


@settings_bp.get("")
def get_settings():
    _require_auth()
    return _serialize(Settings.get_or_create())


@settings_bp.patch("")
@settings_bp.input(SettingsPatchIn)
def update_settings(json_data):
    _require_auth()
    s = Settings.get_or_create()
    s.no_data_behavior = json_data["no_data_behavior"]
    s.save()
    return _serialize(s)

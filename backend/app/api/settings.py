from flask import session, abort
from apiflask import APIBlueprint
from marshmallow import Schema, fields, validate

from app.models.settings import Settings, NO_DATA_BEHAVIORS, THEME_CHOICES

settings_bp = APIBlueprint("settings", __name__, url_prefix="/api/v1/admin/settings")


class SettingsPatchIn(Schema):
    no_data_behavior       = fields.String(validate=validate.OneOf(NO_DATA_BEHAVIORS))
    site_title             = fields.String()
    default_theme          = fields.String(validate=validate.OneOf(THEME_CHOICES))
    show_incident_timeline = fields.Boolean()
    incident_timeline_days = fields.Integer(validate=validate.Range(min=1, max=90))
    wide_layout            = fields.Boolean()


def _require_auth():
    if not session.get("logged_in"):
        abort(401)


def _serialize(s):
    return {
        "no_data_behavior":       s.no_data_behavior,
        "site_title":             s.site_title or "MOSSBoard",
        "default_theme":          s.default_theme or "dark",
        "show_incident_timeline": bool(s.show_incident_timeline),
        "incident_timeline_days": s.incident_timeline_days or 7,
        "wide_layout":            bool(s.wide_layout),
    }


@settings_bp.get("")
def get_settings():
    _require_auth()
    return _serialize(Settings.get_or_create())


@settings_bp.patch("")
@settings_bp.input(SettingsPatchIn)
def update_settings(json_data):
    _require_auth()
    s = Settings.get_or_create()
    if "no_data_behavior"       in json_data: s.no_data_behavior       = json_data["no_data_behavior"]
    if "site_title"             in json_data: s.site_title             = json_data["site_title"].strip() or "MOSSBoard"
    if "default_theme"          in json_data: s.default_theme          = json_data["default_theme"]
    if "show_incident_timeline" in json_data: s.show_incident_timeline = json_data["show_incident_timeline"]
    if "incident_timeline_days" in json_data: s.incident_timeline_days = json_data["incident_timeline_days"]
    if "wide_layout"            in json_data: s.wide_layout            = json_data["wide_layout"]
    s.save()
    return _serialize(s)

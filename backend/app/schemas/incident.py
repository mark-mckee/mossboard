from apiflask import Schema
from apiflask.fields import String, DateTime, List, Nested
from apiflask.validators import Length, OneOf

INCIDENT_STATUS = ["investigating", "identified", "monitoring", "resolved"]


class IncidentUpdateIn(Schema):
    status = String(required=True, validate=OneOf(INCIDENT_STATUS))
    message = String(required=True, validate=Length(min=1))


class IncidentIn(Schema):
    service_id = String(required=True)
    title = String(required=True, validate=Length(min=1, max=300))
    status = String(required=True, validate=OneOf(INCIDENT_STATUS))
    message = String(required=True, validate=Length(min=1))


class IncidentPatchIn(Schema):
    title = String(validate=Length(min=1, max=300))
    resolved = String()  # pass "true" to resolve


class IncidentUpdateOut(Schema):
    status = String()
    message = String()
    created_at = DateTime()


class IncidentOut(Schema):
    id = String(attribute="_id_str")
    service_id = String(attribute="_service_id_str")
    title = String()
    updates = List(Nested(IncidentUpdateOut))
    resolved_at = DateTime(allow_none=True)
    created_at = DateTime()

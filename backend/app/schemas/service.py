from apiflask import Schema
from apiflask.fields import String, Integer, Boolean, DateTime
from apiflask.validators import Length, OneOf

STATUS_CHOICES = [
    "operational",
    "performance_issues",
    "partial_outage",
    "major_outage",
    "unknown",
    "under_maintenance",
]


class ServiceIn(Schema):
    section_id = String(required=True)
    name = String(required=True, validate=Length(min=1, max=200))
    description = String(load_default="")
    status = String(load_default="unknown", validate=OneOf(STATUS_CHOICES))
    order = Integer(load_default=0)
    visible = Boolean(load_default=True)


class ServicePatchIn(Schema):
    section_id = String()
    name = String(validate=Length(min=1, max=200))
    description = String()
    status = String(validate=OneOf(STATUS_CHOICES))
    order = Integer()
    visible = Boolean()


class ServiceStatusIn(Schema):
    status = String(required=True, validate=OneOf(STATUS_CHOICES))


class ServiceOut(Schema):
    id = String(attribute="_id_str")
    section_id = String(attribute="_section_id_str")
    name = String()
    slug = String()
    description = String()
    status = String()
    order = Integer()
    visible = Boolean()
    created_at = DateTime()
    updated_at = DateTime()


class SnapshotOut(Schema):
    status = String()
    recorded_at = DateTime()

from datetime import datetime
from mongoengine import (
    Document, StringField, IntField, BooleanField, DateTimeField,
    ReferenceField, CASCADE,
)

STATUS_CHOICES = [
    "operational",
    "performance_issues",
    "partial_outage",
    "major_outage",
    "unknown",
    "under_maintenance",
]


class Service(Document):
    section = ReferenceField("Section", reverse_delete_rule=CASCADE)
    name = StringField(required=True)
    slug = StringField(required=True, unique=True)
    description = StringField(default="")
    status = StringField(choices=STATUS_CHOICES, default="unknown")
    order = IntField(default=0)
    visible = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    # Optional staleness detection: if the service status has not been updated
    # for this many seconds, a periodic task will set the status to "unknown".
    # null / 0 = disabled.
    stale_after_seconds = IntField(null=True)
    # Tracks the last time the status was explicitly set (by admin, API token, or monitor).
    # Used by the staleness task. Updated independently of updated_at.
    status_updated_at = DateTimeField(default=datetime.utcnow)

    meta = {"ordering": ["order"]}


class StatusSnapshot(Document):
    service = ReferenceField(Service, reverse_delete_rule=CASCADE)
    status = StringField(choices=STATUS_CHOICES)
    note = StringField(default="")
    recorded_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "indexes": [
            {"fields": ["service", "-recorded_at"]},
            {"fields": ["recorded_at"], "expireAfterSeconds": 86400 * 30},
        ]
    }

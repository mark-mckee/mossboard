from datetime import datetime
from mongoengine import (
    Document, StringField, DateTimeField, ListField,
    ReferenceField, BooleanField, DictField, IntField,
)

TRIGGER_CHOICES = [
    "maintenance_created",
    "maintenance_started",
    "maintenance_ended",
    "incident_created",
    "incident_updated",
    "incident_resolved",
    "monitor_status_change",
]

DEST_TYPE_CHOICES = ["webhook", "email"]


class NotificationDestination(Document):
    """A delivery channel — HTTP webhook or email address."""
    name   = StringField(required=True)
    type   = StringField(choices=DEST_TYPE_CHOICES, required=True)

    # Webhook
    url           = StringField(default="")
    method        = StringField(default="POST")
    headers       = DictField()           # static extra headers
    body_template = StringField(default="")   # JSON template with {{var}} placeholders

    # Email
    email_to               = StringField(default="")
    email_subject_template = StringField(default="")
    email_body_template    = StringField(default="")

    active     = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {"ordering": ["name"]}


class NotificationRule(Document):
    """Links a trigger event to a destination, with optional filters."""
    name        = StringField(required=True)
    trigger     = StringField(choices=TRIGGER_CHOICES, required=True)
    destination = ReferenceField(NotificationDestination, required=True)

    # Filters for monitor_status_change (empty string = any)
    filter_from_status = StringField(default="")
    filter_to_status   = StringField(default="")

    # Service filter — empty = all services
    services = ListField(ReferenceField("Service"))

    active     = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {"ordering": ["name"]}

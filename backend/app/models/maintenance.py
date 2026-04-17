from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, ListField, ReferenceField, BooleanField

RECURRENCE_CHOICES = ["none", "daily", "weekly", "monthly"]


class ScheduledMaintenance(Document):
    # Legacy single-service field kept for backwards compat with existing documents.
    # New code writes to `services` only; serializers merge both.
    service     = ReferenceField("Service", null=True)
    services    = ListField(ReferenceField("Service"))
    title       = StringField(required=True)
    description = StringField(default="")
    starts_at   = DateTimeField(required=True)
    ends_at     = DateTimeField(required=True)
    # When True: automatically set service status to under_maintenance on start,
    # and back to operational on end (unless another active window still applies).
    auto_status = BooleanField(default=False)
    # Internal tracking: True while the auto status has been applied.
    auto_status_applied = BooleanField(default=False)
    # Recurrence: none | daily | weekly | monthly
    recurrence  = StringField(choices=RECURRENCE_CHOICES, default="none")
    # For weekly: 0=Mon … 6=Sun displayed in UI (derived from starts_at, stored for display)
    # For monthly: 1–31 (day of month, derived from starts_at, stored for display)
    recurrence_day = StringField(default="")
    created_at  = DateTimeField(default=datetime.utcnow)

    meta = {"ordering": ["starts_at"]}

from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, ReferenceField, BooleanField, CASCADE


class ScheduledMaintenance(Document):
    service = ReferenceField("Service", reverse_delete_rule=CASCADE)
    title = StringField(required=True)
    description = StringField(default="")
    starts_at = DateTimeField(required=True)
    ends_at = DateTimeField(required=True)
    # When True: automatically set service status to under_maintenance on start,
    # and back to operational on end (unless another active window still applies).
    auto_status = BooleanField(default=False)
    # Internal tracking: True while the auto status has been applied.
    auto_status_applied = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {"ordering": ["starts_at"]}

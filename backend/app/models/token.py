from datetime import datetime
from mongoengine import (
    Document, StringField, BooleanField, DateTimeField,
    ListField, ReferenceField,
)


class APIToken(Document):
    name         = StringField(required=True)
    token_hash   = StringField(required=True, unique=True)
    token_prefix = StringField(required=True)
    services     = ListField(ReferenceField("Service"))   # empty = all services
    metrics      = ListField(ReferenceField("Metric"))    # empty = all metrics
    active       = BooleanField(default=True)
    created_at   = DateTimeField(default=datetime.utcnow)
    last_used    = DateTimeField(null=True)

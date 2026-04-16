from datetime import datetime
from mongoengine import (
    Document, StringField, BooleanField, DateTimeField,
    ListField, ReferenceField,
)


class APIToken(Document):
    name                   = StringField(required=True)
    token_hash             = StringField(required=True, unique=True)
    token_prefix           = StringField(required=True)
    allow_service_updates  = BooleanField(default=True)   # master switch for PATCH /services/*/status
    services               = ListField(ReferenceField("Service"))   # empty = all services (when allowed)
    allow_metric_pushes    = BooleanField(default=True)   # master switch for POST /metrics/*/points
    metrics                = ListField(ReferenceField("Metric"))    # empty = all metrics (when allowed)
    active                 = BooleanField(default=True)
    created_at             = DateTimeField(default=datetime.utcnow)
    last_used              = DateTimeField(null=True)

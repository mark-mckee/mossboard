from datetime import datetime
from mongoengine import (
    Document, StringField, FloatField, IntField, BooleanField,
    DateTimeField, ReferenceField, CASCADE,
)

VIEW_CHOICES = ["last_hour", "today", "week", "month"]
TYPE_CHOICES = ["sum", "average", "last"]


class Metric(Document):
    """A named time-series metric attached to a service."""

    service       = ReferenceField("Service", reverse_delete_rule=CASCADE)
    name          = StringField(required=True)
    suffix        = StringField(default="")
    description   = StringField(default="")
    default_view  = StringField(choices=VIEW_CHOICES, default="last_hour")
    default_value = FloatField(default=0)
    display_chart = BooleanField(default=True)
    places        = IntField(default=0)
    metric_type   = StringField(choices=TYPE_CHOICES, default="average")
    threshold     = IntField(default=0)   # seconds; 0 = always create a new point
    visible       = BooleanField(default=True)
    created_at    = DateTimeField(default=datetime.utcnow)

    meta = {"collection": "metrics", "ordering": ["name"]}


class MetricPoint(Document):
    """A single data point for a metric."""

    metric    = ReferenceField(Metric, reverse_delete_rule=CASCADE)
    value     = FloatField(required=True)
    count     = IntField(default=1)       # number of samples merged (for running average)
    timestamp = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "metric_points",
        "indexes": [
            {"fields": ["metric", "-timestamp"]},
            {"fields": ["timestamp"], "expireAfterSeconds": 86400 * 30},  # TTL 30 days
        ],
    }

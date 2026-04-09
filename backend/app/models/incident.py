from datetime import datetime
from mongoengine import (
    Document, EmbeddedDocument, StringField, DateTimeField,
    ReferenceField, EmbeddedDocumentListField, CASCADE,
)

INCIDENT_STATUS = ["investigating", "identified", "monitoring", "resolved"]


class IncidentUpdate(EmbeddedDocument):
    status = StringField(choices=INCIDENT_STATUS)
    message = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)


class Incident(Document):
    service = ReferenceField("Service", reverse_delete_rule=CASCADE)
    title = StringField(required=True)
    updates = EmbeddedDocumentListField(IncidentUpdate)
    resolved_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {"ordering": ["-created_at"]}

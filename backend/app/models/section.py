from datetime import datetime
from mongoengine import Document, StringField, IntField, BooleanField, DateTimeField


class Section(Document):
    name = StringField(required=True)
    slug = StringField(required=True, unique=True)
    order = IntField(default=0)
    visible = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {"ordering": ["order"]}

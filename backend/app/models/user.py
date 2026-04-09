from datetime import datetime
from mongoengine import Document, StringField, BooleanField, DateTimeField


class User(Document):
    username = StringField(required=True, unique=True)
    password_hash = StringField(required=True)
    role = StringField(choices=["admin", "viewer"], default="admin")
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    last_login = DateTimeField(null=True)

    meta = {"ordering": ["username"]}

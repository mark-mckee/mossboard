from mongoengine import Document, StringField

NO_DATA_BEHAVIORS = ["unknown", "operational", "exclude"]


class Settings(Document):
    """Global application settings — singleton, always exactly one document."""

    no_data_behavior = StringField(
        choices=NO_DATA_BEHAVIORS,
        default="unknown",
    )

    meta = {"collection": "settings"}

    @classmethod
    def get_or_create(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls(no_data_behavior="unknown")
            obj.save()
        return obj

from mongoengine import Document, StringField, BooleanField, IntField

NO_DATA_BEHAVIORS = ["unknown", "operational", "exclude"]
THEME_CHOICES     = ["dark", "light"]


class Settings(Document):
    """Global application settings — singleton, always exactly one document."""

    no_data_behavior        = StringField(choices=NO_DATA_BEHAVIORS, default="unknown")
    site_title              = StringField(default="MOSSBoard")
    default_theme           = StringField(choices=THEME_CHOICES, default="dark")
    show_incident_timeline  = BooleanField(default=False)
    incident_timeline_days  = IntField(default=7)
    wide_layout             = BooleanField(default=False)

    meta = {"collection": "settings"}

    @classmethod
    def get_or_create(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls(
                no_data_behavior="unknown",
                site_title="MOSSBoard",
                default_theme="dark",
                show_incident_timeline=False,
                incident_timeline_days=7,
                wide_layout=False,
            )
            obj.save()
        return obj

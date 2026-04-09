from apiflask import Schema
from apiflask.fields import String, Integer, Boolean, DateTime
from apiflask.validators import Length, OneOf


class SectionIn(Schema):
    name = String(required=True, validate=Length(min=1, max=200))
    order = Integer(load_default=0)
    visible = Boolean(load_default=True)


class SectionPatchIn(Schema):
    name = String(validate=Length(min=1, max=200))
    order = Integer()
    visible = Boolean()


class SectionOut(Schema):
    id = String(attribute="_id_str")
    name = String()
    slug = String()
    order = Integer()
    visible = Boolean()
    created_at = DateTime()

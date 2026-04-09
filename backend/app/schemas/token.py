from apiflask import Schema
from apiflask.fields import String, Boolean, DateTime, List
from apiflask.validators import Length


class TokenIn(Schema):
    name = String(required=True, validate=Length(min=1, max=200))
    service_ids = List(String(), load_default=[])


class TokenOut(Schema):
    id = String(attribute="_id_str")
    name = String()
    token_prefix = String()
    service_ids = List(String(), attribute="_service_id_strs")
    active = Boolean()
    created_at = DateTime()
    last_used = DateTime(allow_none=True)


class TokenCreatedOut(Schema):
    id = String(attribute="_id_str")
    name = String()
    token = String()
    token_prefix = String()
    service_ids = List(String(), attribute="_service_id_strs")
    active = Boolean()
    created_at = DateTime()

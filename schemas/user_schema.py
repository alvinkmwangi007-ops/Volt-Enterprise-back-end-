"""schemas/user_schema.py"""

from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    full_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    phone_number = fields.Str(required=True, validate=validate.Length(min=7, max=20))
    role = fields.Str(validate=validate.OneOf(["buyer", "seller", "admin"]), load_default="buyer")
    is_verified = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    password = fields.Str(load_only=True, required=True, validate=validate.Length(min=8))


user_schema = UserSchema()
users_schema = UserSchema(many=True)
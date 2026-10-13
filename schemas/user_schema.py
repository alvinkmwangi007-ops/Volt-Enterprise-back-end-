"""schemas/user_schema.py"""

from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    full_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    phone_number = fields.Str(required=True, validate=validate.Length(min=7, max=20))
    role = fields.Str(dump_only=True)
    is_verified = fields.Bool(dump_only=True)
    interest_notifications = fields.Bool(dump_only=True)
    national_id = fields.Str(load_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    password = fields.Str(load_only=True, required=False, validate=validate.Length(min=8))


user_schema = UserSchema()
users_schema = UserSchema(many=True)


class UserProfileSchema(UserSchema):
    national_id = fields.Str(dump_only=True)


user_profile_schema = UserProfileSchema()
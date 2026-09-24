"""schemas/car_schema.py"""

from marshmallow import Schema, fields, validate


class CarImageSchema(Schema):
    id = fields.Int(dump_only=True)
    car_id = fields.Int(dump_only=True)
    image_url = fields.Str(required=True)
    is_primary = fields.Bool(load_default=False)
    uploaded_at = fields.DateTime(dump_only=True)


class CarSchema(Schema):
    id = fields.Int(dump_only=True)
    seller_id = fields.Int(dump_only=True)
    make = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    model = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    year = fields.Int(required=True, validate=validate.Range(min=1980, max=2100))
    mileage = fields.Int(required=True, validate=validate.Range(min=0))
    price = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))
    fuel_type = fields.Str(required=True, validate=validate.OneOf(
        ["petrol", "diesel", "hybrid", "electric"]
    ))
    transmission = fields.Str(required=True, validate=validate.OneOf(["manual", "automatic"]))
    condition_notes = fields.Str(required=False, allow_none=True)
    location = fields.Str(required=False, allow_none=True)
    status = fields.Str(dump_only=True)
    verification_status = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    images = fields.List(fields.Nested(CarImageSchema), dump_only=True)


car_schema = CarSchema()
cars_schema = CarSchema(many=True)
car_image_schema = CarImageSchema()
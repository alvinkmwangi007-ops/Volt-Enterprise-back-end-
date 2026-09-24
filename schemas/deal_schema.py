"""schemas/deal_schema.py"""

from marshmallow import Schema, fields, validate


class BrokerageDealSchema(Schema):
    id = fields.Int(dump_only=True)
    car_id = fields.Int(required=True)
    buyer_id = fields.Int(required=True)
    seller_id = fields.Int(required=True)
    inquiry_id = fields.Int(required=False, allow_none=True)
    agreed_price = fields.Decimal(required=True, as_string=True, validate=validate.Range(min=0))
    commission_rate = fields.Decimal(required=False, as_string=True, validate=validate.Range(min=0, max=100))
    commission_amount = fields.Decimal(dump_only=True, as_string=True)
    status = fields.Str(dump_only=True)
    closed_at = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


brokerage_deal_schema = BrokerageDealSchema()
brokerage_deals_schema = BrokerageDealSchema(many=True)
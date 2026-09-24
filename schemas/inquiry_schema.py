"""schemas/inquiry_schema.py"""

from marshmallow import Schema, fields, validate


class MessageSchema(Schema):
    id = fields.Int(dump_only=True)
    inquiry_id = fields.Int(dump_only=True)
    sender_id = fields.Int(dump_only=True)
    body = fields.Str(required=True, validate=validate.Length(min=1))
    sent_at = fields.DateTime(dump_only=True)


class InquirySchema(Schema):
    id = fields.Int(dump_only=True)
    car_id = fields.Int(required=True)
    buyer_id = fields.Int(dump_only=True)
    seller_id = fields.Int(dump_only=True)
    status = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    messages = fields.List(fields.Nested(MessageSchema), dump_only=True)


inquiry_schema = InquirySchema()
inquiries_schema = InquirySchema(many=True)
message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)
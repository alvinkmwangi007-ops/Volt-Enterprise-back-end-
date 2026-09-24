from marshmallow import Schema, fields, validate


class InspectionPartnerSchema(Schema):
	id = fields.Int(dump_only=True)
	name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
	contact_email = fields.Email(required=False, allow_none=True)
	contact_phone = fields.Str(required=False, allow_none=True)
	api_endpoint = fields.Str(required=False, allow_none=True)
	is_active = fields.Bool(load_default=True)


class InspectionSchema(Schema):
	id = fields.Int(dump_only=True)
	car_id = fields.Int(required=True)
	partner_id = fields.Int(required=True)
	requested_by = fields.Int(dump_only=True)
	status = fields.Str(dump_only=True)
	scheduled_at = fields.DateTime(required=False, allow_none=True)
	completed_at = fields.DateTime(dump_only=True)
	report_url = fields.Str(dump_only=True)
	result = fields.Str(dump_only=True)
	notes = fields.Str(required=False, allow_none=True)
	created_at = fields.DateTime(dump_only=True)


inspection_partner_schema = InspectionPartnerSchema()
inspection_partners_schema = InspectionPartnerSchema(many=True)
inspection_schema = InspectionSchema()
inspections_schema = InspectionSchema(many=True)

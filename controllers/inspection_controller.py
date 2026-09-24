from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from database import get_session
from Models import Car, Inspection
from schemas import inspection_schema, inspections_schema
from utils.decorators import role_required


inspection_bp = Blueprint(
    "inspections",
    __name__,
    url_prefix="/api/inspections",
)


@inspection_bp.route("", methods=["POST"])
@role_required("seller", "admin")
def request_inspection():
    db = get_session()
    try:
        try:
            data = inspection_schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({"errors": err.messages}), 400

        car = db.get(Car, data["car_id"])
        if not car:
            return jsonify({"error": "Car not found"}), 404

        requested_by = int(get_jwt_identity())
        new_inspection = Inspection(requested_by=requested_by, **data)
        db.add(new_inspection)
        car.verification_status = "pending"
        db.commit()
        db.refresh(new_inspection)
        return jsonify(inspection_schema.dump(new_inspection)), 201
    except Exception as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400
    finally:
        db.close()


@inspection_bp.route("/<int:inspection_id>/result", methods=["PATCH"])
def submit_inspection_result(inspection_id):
    provided_key = request.headers.get("X-Partner-Api-Key")
    expected_key = current_app.config.get("INSPECTION_PARTNER_API_KEY")
    if not provided_key or provided_key != expected_key:
        return jsonify({"error": "Invalid or missing partner API key"}), 401

    db = get_session()
    try:
        inspection = db.get(Inspection, inspection_id)
        if not inspection:
            return jsonify({"error": "Inspection not found"}), 404

        body = request.get_json() or {}
        result = body.get("result")
        report_url = body.get("report_url")
        if result not in ("pass", "fail", "flagged"):
            return jsonify({
                "error": "result must be one of pass, fail, flagged",
            }), 400

        inspection.result = result
        inspection.status = "completed"
        inspection.report_url = report_url

        car = db.get(Car, inspection.car_id)
        if car:
            car.verification_status = "verified" if result == "pass" else "rejected"

        db.commit()
        db.refresh(inspection)
        return jsonify(inspection_schema.dump(inspection)), 200
    except Exception as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400
    finally:
        db.close()


@inspection_bp.route("/car/<int:car_id>", methods=["GET"])
@jwt_required()
def list_inspections_for_car(car_id):
    db = get_session()
    try:
        results = db.query(Inspection).filter(Inspection.car_id == car_id).all()
        return jsonify(inspections_schema.dump(results)), 200
    finally:
        db.close()

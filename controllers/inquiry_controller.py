from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from database import get_session
from Models import Car, Inquiry, Message
from schemas import inquiry_schema, inquiries_schema, message_schema
from utils.decorators import role_required


inquiry_bp = Blueprint("inquiries", __name__, url_prefix="/api/inquiries")


def _is_participant_or_admin(inquiry, requester_id, requester_role):
    return (
        requester_role == "admin"
        or str(inquiry.buyer_id) == requester_id
        or str(inquiry.seller_id) == requester_id
    )


@inquiry_bp.route("", methods=["POST"])
@role_required("buyer", "admin")
def start_inquiry():
    db = get_session()
    try:
        try:
            data = inquiry_schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({"errors": err.messages}), 400

        car = db.get(Car, data["car_id"])
        if not car:
            return jsonify({"error": "Car not found"}), 404

        buyer_id = int(get_jwt_identity())
        new_inquiry = Inquiry(
            car_id=data["car_id"],
            buyer_id=buyer_id,
            seller_id=car.seller_id,
        )
        db.add(new_inquiry)
        db.commit()
        db.refresh(new_inquiry)
        return jsonify(inquiry_schema.dump(new_inquiry)), 201
    except Exception as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400
    finally:
        db.close()


@inquiry_bp.route("/<int:inquiry_id>/messages", methods=["POST"])
@jwt_required()
def send_message(inquiry_id):
    db = get_session()
    try:
        inquiry = db.get(Inquiry, inquiry_id)
        if not inquiry:
            return jsonify({"error": "Inquiry not found"}), 404

        requester_id = get_jwt_identity()
        requester_role = get_jwt().get("role")
        if not _is_participant_or_admin(inquiry, requester_id, requester_role):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = message_schema.load(request.get_json() or {})
        new_message = Message(
            inquiry_id=inquiry_id,
            sender_id=int(requester_id),
            **data,
        )
        db.add(new_message)
        if inquiry.status == "open":
            inquiry.status = "in_discussion"

        db.commit()
        db.refresh(new_message)
        return jsonify(message_schema.dump(new_message)), 201
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    except Exception as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400
    finally:
        db.close()


@inquiry_bp.route("/<int:inquiry_id>", methods=["GET"])
@jwt_required()
def get_inquiry(inquiry_id):
    db = get_session()
    try:
        inquiry = db.get(Inquiry, inquiry_id)
        if not inquiry:
            return jsonify({"error": "Inquiry not found"}), 404

        requester_id = get_jwt_identity()
        requester_role = get_jwt().get("role")
        if not _is_participant_or_admin(inquiry, requester_id, requester_role):
            return jsonify({"error": "Insufficient permissions"}), 403

        return jsonify(inquiry_schema.dump(inquiry)), 200
    finally:
        db.close()


@inquiry_bp.route("/user/<int:user_id>", methods=["GET"])
@jwt_required()
def list_inquiries_for_user(user_id):
    db = get_session()
    try:
        requester_id = get_jwt_identity()
        requester_role = get_jwt().get("role")
        if str(user_id) != requester_id and requester_role != "admin":
            return jsonify({"error": "Insufficient permissions"}), 403

        results = db.query(Inquiry).filter(
            (Inquiry.buyer_id == user_id) | (Inquiry.seller_id == user_id)
        ).all()
        return jsonify(inquiries_schema.dump(results)), 200
    finally:
        db.close()

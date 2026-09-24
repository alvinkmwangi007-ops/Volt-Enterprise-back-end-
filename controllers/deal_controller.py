from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from database import get_session
from Models import BrokerageDeal, Car
from schemas import brokerage_deal_schema, brokerage_deals_schema
from utils.decorators import role_required


deal_bp = Blueprint("deals", __name__, url_prefix="/api/deals")

DEFAULT_COMMISSION_RATE = 5.00


@deal_bp.route("", methods=["POST"])
@role_required("admin")
def open_brokerage_deal():
    db = get_session()
    try:
        try:
            data = brokerage_deal_schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({"errors": err.messages}), 400

        car = db.get(Car, data["car_id"])
        if not car:
            return jsonify({"error": "Car not found"}), 404

        commission_rate = data.get("commission_rate", DEFAULT_COMMISSION_RATE)
        agreed_price = data["agreed_price"]
        commission_amount = round(
            float(agreed_price) * float(commission_rate) / 100,
            2,
        )

        new_deal = BrokerageDeal(
            car_id=data["car_id"],
            buyer_id=data["buyer_id"],
            seller_id=data["seller_id"],
            inquiry_id=data.get("inquiry_id"),
            agreed_price=agreed_price,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
        )
        db.add(new_deal)
        car.status = "pending_sale"
        db.commit()
        db.refresh(new_deal)
        return jsonify(brokerage_deal_schema.dump(new_deal)), 201
    except Exception as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400
    finally:
        db.close()


@deal_bp.route("/<int:deal_id>/status", methods=["PATCH"])
@role_required("admin")
def update_deal_status(deal_id):
    db = get_session()
    try:
        deal = db.get(BrokerageDeal, deal_id)
        if not deal:
            return jsonify({"error": "Deal not found"}), 404

        new_status = (request.get_json() or {}).get("status")
        valid_statuses = (
            "negotiating",
            "agreed",
            "payment_pending",
            "completed",
            "cancelled",
        )
        if new_status not in valid_statuses:
            return jsonify({"error": f"status must be one of {valid_statuses}"}), 400

        deal.status = new_status
        car = db.get(Car, deal.car_id)
        if car:
            if new_status == "completed":
                car.status = "sold"
                deal.closed_at = datetime.utcnow()
            elif new_status == "cancelled":
                car.status = "active"

        db.commit()
        db.refresh(deal)
        return jsonify(brokerage_deal_schema.dump(deal)), 200
    except Exception as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400
    finally:
        db.close()


@deal_bp.route("/<int:deal_id>", methods=["GET"])
@jwt_required()
def get_deal(deal_id):
    db = get_session()
    try:
        deal = db.get(BrokerageDeal, deal_id)
        if not deal:
            return jsonify({"error": "Deal not found"}), 404
        return jsonify(brokerage_deal_schema.dump(deal)), 200
    finally:
        db.close()


@deal_bp.route("", methods=["GET"])
@role_required("admin")
def list_deals():
    db = get_session()
    try:
        results = db.query(BrokerageDeal).all()
        return jsonify(brokerage_deals_schema.dump(results)), 200
    finally:
        db.close()

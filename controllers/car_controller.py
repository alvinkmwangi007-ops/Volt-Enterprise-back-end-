from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from database import get_session
from Models import Car, CarImage, CarStatus
from schemas import car_image_schema, car_schema, cars_schema
from utils.decorators import role_required


car_bp = Blueprint("cars", __name__, url_prefix="/api/cars")


@car_bp.route("/mine", methods=["GET"])
@role_required("seller", "admin", "manager")
def find_my_cars():
    db = get_session()
    try:
        requester_id = int(get_jwt_identity())
        requester_role = get_jwt().get("role")
        query = db.query(Car)
        if requester_role not in {"admin", "manager"}:
            query = query.filter(Car.seller_id == requester_id)
        return jsonify(cars_schema.dump(query.order_by(Car.id.desc()).all())), 200
    finally:
        db.close()


@car_bp.route("", methods=["POST"])
@role_required("seller", "admin", "manager")
def list_a_car():
    db = get_session()
    try:
        try:
            data = car_schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({"errors": err.messages}), 400

        seller_id = int(get_jwt_identity())
        new_car = Car(seller_id=seller_id, status=CarStatus.active, **data)
        db.add(new_car)
        db.commit()
        db.refresh(new_car)
        return jsonify(car_schema.dump(new_car)), 201
    except Exception:
        db.rollback()
        return jsonify({"error": "The vehicle listing could not be saved."}), 500
    finally:
        db.close()


@car_bp.route("", methods=["GET"])
def find_a_car():
    db = get_session()
    try:
        query = db.query(Car).filter(Car.status == "active")

        make = request.args.get("make")
        if make:
            query = query.filter(Car.make.ilike(f"%{make}%"))

        model = request.args.get("model")
        if model:
            query = query.filter(Car.model.ilike(f"%{model}%"))

        min_price = request.args.get("min_price", type=float)
        if min_price is not None:
            query = query.filter(Car.price >= min_price)

        max_price = request.args.get("max_price", type=float)
        if max_price is not None:
            query = query.filter(Car.price <= max_price)

        fuel_type = request.args.get("fuel_type")
        if fuel_type:
            query = query.filter(Car.fuel_type == fuel_type)

        transmission = request.args.get("transmission")
        if transmission:
            query = query.filter(Car.transmission == transmission)

        location = request.args.get("location")
        if location:
            query = query.filter(Car.location.ilike(f"%{location}%"))

        return jsonify(cars_schema.dump(query.all())), 200
    finally:
        db.close()


@car_bp.route("/<int:car_id>", methods=["GET"])
def get_car(car_id):
    db = get_session()
    try:
        car = db.get(Car, car_id)
        if not car or str(car.status) not in {"active", "CarStatus.active"}:
            return jsonify({"error": "Car not found"}), 404
        return jsonify(car_schema.dump(car)), 200
    finally:
        db.close()


@car_bp.route("/<int:car_id>", methods=["PATCH"])
@jwt_required()
def update_car(car_id):
    db = get_session()
    try:
        car = db.get(Car, car_id)
        if not car:
            return jsonify({"error": "Car not found"}), 404
        requester_id = get_jwt_identity()
        requester_role = get_jwt().get("role")
        if requester_role != "admin" and str(car.seller_id) != requester_id:
            return jsonify({"error": "Insufficient permissions"}), 403
        try:
            body = request.get_json() or {}
            data = car_schema.load(body, partial=True)
        except ValidationError as err:
            return jsonify({"errors": err.messages}), 400
        if not data:
            return jsonify({"error": "Provide at least one editable vehicle field."}), 400
        for field, value in data.items():
            setattr(car, field, value)
        db.commit()
        db.refresh(car)
        return jsonify(car_schema.dump(car)), 200
    except Exception:
        db.rollback()
        return jsonify({"error": "The vehicle listing could not be updated."}), 500
    finally:
        db.close()


@car_bp.route("/<int:car_id>", methods=["DELETE"])
@jwt_required()
def remove_car(car_id):
    db = get_session()
    try:
        car = db.get(Car, car_id)
        if not car:
            return jsonify({"error": "Car not found"}), 404
        requester_id = get_jwt_identity()
        requester_role = get_jwt().get("role")
        if str(car.seller_id) != requester_id and requester_role not in {"admin", "manager"}:
            return jsonify({"error": "Insufficient permissions"}), 403
        car.status = CarStatus.removed
        db.commit()
        return "", 204
    except Exception:
        db.rollback()
        return jsonify({"error": "The vehicle listing could not be removed."}), 500
    finally:
        db.close()


@car_bp.route("/<int:car_id>/images", methods=["POST"])
@jwt_required()
def add_car_image(car_id):
    db = get_session()
    try:
        car = db.get(Car, car_id)
        if not car:
            return jsonify({"error": "Car not found"}), 404

        requester_id = get_jwt_identity()
        requester_role = get_jwt().get("role")
        if str(car.seller_id) != requester_id and requester_role != "admin":
            return jsonify({"error": "Insufficient permissions"}), 403

        data = car_image_schema.load(request.get_json() or {})
        image = CarImage(car_id=car_id, **data)
        db.add(image)
        db.commit()
        db.refresh(image)
        return jsonify(car_image_schema.dump(image)), 201
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    except Exception:
        db.rollback()
        return jsonify({"error": "The vehicle image could not be added."}), 500
    finally:
        db.close()

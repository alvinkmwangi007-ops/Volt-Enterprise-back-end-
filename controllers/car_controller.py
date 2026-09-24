from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from database import get_session
from Models import Car, CarImage
from schemas import car_image_schema, car_schema, cars_schema
from utils.decorators import role_required


car_bp = Blueprint("cars", __name__, url_prefix="/api/cars")


@car_bp.route("", methods=["POST"])
@role_required("seller", "admin")
def list_a_car():
    db = get_session()
    try:
        try:
            data = car_schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({"errors": err.messages}), 400

        seller_id = int(get_jwt_identity())
        new_car = Car(seller_id=seller_id, **data)
        db.add(new_car)
        db.commit()
        db.refresh(new_car)
        return jsonify(car_schema.dump(new_car)), 201
    except Exception as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400
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
        if not car:
            return jsonify({"error": "Car not found"}), 404
        return jsonify(car_schema.dump(car)), 200
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
    except Exception as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400
    finally:
        db.close()

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from database import get_session
from Models import User
from schemas import user_schema, users_schema
from utils.decorators import role_required


user_bp = Blueprint("users", __name__, url_prefix="/api/users")


@user_bp.route("", methods=["GET"])
@role_required("admin")
def list_users():
    """Admin only: list every user on the platform."""
    db = get_session()
    try:
        all_users = db.query(User).all()
        return jsonify(users_schema.dump(all_users)), 200
    finally:
        db.close()


@user_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    """A user can view their own profile; admins can view anyone's."""
    db = get_session()
    try:
        requester_id = get_jwt_identity()
        requester_role = get_jwt().get("role")

        if str(user_id) != requester_id and requester_role != "admin":
            return jsonify({"error": "Insufficient permissions"}), 403

        user = db.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user_schema.dump(user)), 200
    finally:
        db.close()
import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from werkzeug.security import generate_password_hash

from database import get_session
from Models import User
from schemas import user_profile_schema, user_schema, users_schema
from utils.decorators import role_required


user_bp = Blueprint("users", __name__, url_prefix="/api/users")


@user_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    identity = get_jwt_identity()
    db = get_session()
    try:
        user = db.get(User, int(identity))
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user_profile_schema.dump(user)), 200
    finally:
        db.close()


@user_bp.route("/me", methods=["PATCH"])
@jwt_required()
def update_current_user():
    identity = get_jwt_identity()
    body = request.get_json(silent=True) or {}
    allowed = {"full_name", "national_id", "interest_notifications"}
    if not body or set(body) - allowed:
        return jsonify({"error": "Only name, National ID, and notification preference can be updated."}), 400
    db = get_session()
    try:
        user = db.get(User, int(identity))
        if not user:
            return jsonify({"error": "User not found"}), 404
        if "full_name" in body:
            name = str(body["full_name"]).strip()
            if not name or len(name) > 100:
                return jsonify({"error": "Enter a valid full name."}), 400
            user.full_name = name
        if "national_id" in body:
            national_id = str(body["national_id"]).strip()
            if not national_id or len(national_id) > 32:
                return jsonify({"error": "Enter a valid National ID number."}), 400
            user.national_id = national_id
        if "interest_notifications" in body:
            if not isinstance(body["interest_notifications"], bool):
                return jsonify({"error": "Notification preference must be true or false."}), 400
            user.interest_notifications = body["interest_notifications"]
        db.commit()
        db.refresh(user)
        return jsonify(user_profile_schema.dump(user)), 200
    except Exception:
        db.rollback()
        return jsonify({"error": "Profile could not be updated."}), 500
    finally:
        db.close()


@user_bp.route("", methods=["GET"])
@role_required("admin", "manager")
def list_users():
    """Managers and admins can view customer/account rows."""
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

        if str(user_id) != requester_id and requester_role not in {"admin", "manager"}:
            return jsonify({"error": "Insufficient permissions"}), 403

        user = db.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user_schema.dump(user)), 200
    finally:
        db.close()
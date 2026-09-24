from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_session
from Models import User
from schemas import user_schema


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _role_value(user):
    role = user.role
    return role.value if hasattr(role, "value") else role


def _issue_tokens(user):
    claims = {"role": _role_value(user)}
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims=claims,
    )
    refresh_token = create_refresh_token(
        identity=str(user.id),
        additional_claims=claims,
    )
    return access_token, refresh_token


@auth_bp.route("/register", methods=["POST"])
def register():
    db = get_session()
    try:
        try:
            data = user_schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({"errors": err.messages}), 400

        if db.query(User).filter(User.email == data["email"]).first():
            return jsonify({"error": "Email already registered"}), 409

        new_user = User(
            full_name=data["full_name"],
            email=data["email"],
            phone_number=data["phone_number"],
            password_hash=generate_password_hash(data["password"]),
            role=data.get("role", "buyer"),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        access_token, refresh_token = _issue_tokens(new_user)
        return jsonify({
            "user": user_schema.dump(new_user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }), 201
    except Exception as error:
        db.rollback()
        return jsonify({"error": str(error)}), 400
    finally:
        db.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    db = get_session()
    try:
        body = request.get_json() or {}
        email = body.get("email")
        password = body.get("password")
        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        user = db.query(User).filter(User.email == email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid email or password"}), 401

        access_token, refresh_token = _issue_tokens(user)
        return jsonify({
            "user": user_schema.dump(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }), 200
    finally:
        db.close()


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    db = get_session()
    try:
        user = db.get(User, int(identity))
        if not user:
            return jsonify({"error": "User not found"}), 404
        access_token = create_access_token(
            identity=identity,
            additional_claims={"role": _role_value(user)},
        )
        return jsonify({"access_token": access_token}), 200
    finally:
        db.close()


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    identity = get_jwt_identity()
    db = get_session()
    try:
        user = db.get(User, int(identity))
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user_schema.dump(user)), 200
    finally:
        db.close()

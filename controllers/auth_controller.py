import logging
import re
import secrets

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_session
from Models import User
from schemas import user_schema


logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")
ALLOWED_REGISTRATION_ROLES = {"buyer", "seller"}


def _normalize_phone(value):
    if not isinstance(value, str):
        return ""
    phone = re.sub(r"[\s().-]", "", value)
    return phone if PHONE_PATTERN.fullmatch(phone) else ""


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


_google_request = google_requests.Request()


def _verify_firebase_token(id_token):
    """Return the verified Firebase claims, or None if the token is invalid."""
    if not isinstance(id_token, str) or not id_token:
        return None
    try:
        claims = google_id_token.verify_firebase_token(
            id_token,
            _google_request,
            audience=current_app.config["FIREBASE_PROJECT_ID"],
        )
    except Exception as error:
        logger.warning("Firebase token rejected: %s", error)
        return None
    if not claims or not claims.get("email"):
        return None
    return claims


def _auth_response(user, status=200):
    access_token, refresh_token = _issue_tokens(user)
    return jsonify({
        "user": user_schema.dump(user),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }), status


@auth_bp.route("/firebase/register", methods=["POST"])
def firebase_register():
    body = request.form if request.mimetype == "multipart/form-data" else (request.get_json(silent=True) or {})
    claims = _verify_firebase_token(body.get("id_token"))
    if not claims:
        return jsonify({"error": "Invalid or expired sign-in. Please try again."}), 401

    email = claims["email"].strip().lower()
    full_name = str(body.get("full_name") or "").strip()
    phone_number = _normalize_phone(body.get("phone_number"))
    role = body.get("role", "buyer")
    national_id = str(body.get("national_id") or "").strip()
    if (
        not full_name
        or len(full_name) > 100
        or len(email) > 150
        or not phone_number
        or role not in ALLOWED_REGISTRATION_ROLES
        or not national_id
        or len(national_id) > 32
    ):
        return jsonify({
            "error": "Valid name, phone, National ID and buyer or seller role are required.",
        }), 400
    notification_choice = body.get("interest_notifications")
    if role == "seller":
        valid_notification_choice = (
            isinstance(notification_choice, bool)
            or notification_choice in {"true", "false"}
        )
        if not valid_notification_choice:
            return jsonify({"error": "Choose whether to receive interest notifications."}), 400

    db = get_session()
    try:
        if db.query(User).filter(
            (User.email == email) | (User.phone_number == phone_number)
        ).first():
            return jsonify({"error": "An account already uses that email or phone number."}), 409
        new_user = User(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            password_hash=generate_password_hash(secrets.token_urlsafe(32)),
            role=role,
            national_id=national_id,
            interest_notifications=(
                notification_choice is True
                or notification_choice == "true"
            ),
            is_verified=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return _auth_response(new_user, 201)
    except Exception:
        db.rollback()
        logger.exception("Account registration failed.")
        return jsonify({"error": "Account registration failed."}), 500
    finally:
        db.close()


@auth_bp.route("/firebase/login", methods=["POST"])
def firebase_login():
    body = request.get_json(silent=True) or {}
    claims = _verify_firebase_token(body.get("id_token"))
    if not claims:
        return jsonify({"error": "Invalid or expired sign-in. Please try again."}), 401

    db = get_session()
    try:
        user = db.query(User).filter(User.email == claims["email"].strip().lower()).first()
        if not user or not user.is_verified:
            return jsonify({"error": "No Volt account exists for this login. Please sign up first."}), 404
        return _auth_response(user)
    finally:
        db.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    """Password login, used only by manager/admin accounts provisioned on the backend."""
    body = request.get_json(silent=True) or {}
    email = str(body.get("email") or "").strip().lower()
    password = body.get("password")
    if not email or not isinstance(password, str) or not password:
        return jsonify({"error": "Email and password are required."}), 400

    db = get_session()
    try:
        user = db.query(User).filter(User.email == email).first()
        if (
            not user
            or not user.is_verified
            or not check_password_hash(user.password_hash, password)
        ):
            return jsonify({"error": "Invalid email or password."}), 401
        return _auth_response(user)
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
            return jsonify({"error": "User not found."}), 404
        access_token, _ = _issue_tokens(user)
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
            return jsonify({"error": "User not found."}), 404
        return jsonify(user_schema.dump(user)), 200
    finally:
        db.close()

import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_session
from Models import OtpChallenge, User
from schemas import user_schema


logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
OTP_PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")
OTP_CODE_PATTERN = re.compile(r"^\d{6}$")
ALLOWED_REGISTRATION_ROLES = {"buyer", "seller"}


def _normalize_phone(value):
    if not isinstance(value, str):
        return ""
    phone = re.sub(r"[\s().-]", "", value)
    return phone if OTP_PHONE_PATTERN.fullmatch(phone) else ""


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


def _send_sms(phone_number, code):
    sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    token = current_app.config.get("TWILIO_AUTH_TOKEN")
    from_number = current_app.config.get("TWILIO_FROM_NUMBER")
    if not sid or not token or not from_number:
        raise RuntimeError("SMS OTP delivery is not configured.")

    endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    body = urlencode({
        "To": phone_number,
        "From": from_number,
        "Body": f"Your Volt Enterprises verification code is {code}. It expires in 5 minutes.",
    }).encode("utf-8")
    request_message = Request(endpoint, data=body, method="POST")
    request_message.add_header("Authorization", "Basic " + __import__("base64").b64encode(
        f"{sid}:{token}".encode("utf-8")
    ).decode("ascii"))
    request_message.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(request_message, timeout=10) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError("SMS provider rejected the OTP request.")
    except (HTTPError, URLError, TimeoutError) as error:
        logger.warning("OTP SMS delivery failed: %s", error)
        raise RuntimeError("SMS OTP delivery is temporarily unavailable.") from error


def _latest_challenge(db, phone_number, purpose):
    return (
        db.query(OtpChallenge)
        .filter(
            OtpChallenge.phone_number == phone_number,
            OtpChallenge.purpose == purpose,
            OtpChallenge.consumed_at.is_(None),
        )
        .order_by(OtpChallenge.id.desc())
        .first()
    )


def _verify_challenge(db, phone_number, code, purpose):
    challenge = _latest_challenge(db, phone_number, purpose)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not challenge or challenge.expires_at <= now:
        return None, "That verification code has expired. Request a new code."
    if challenge.attempts >= current_app.config["OTP_MAX_ATTEMPTS"]:
        return None, "Too many attempts. Request a new verification code."
    if not OTP_CODE_PATTERN.fullmatch(code) or not check_password_hash(
        challenge.code_hash,
        code,
    ):
        challenge.attempts += 1
        db.commit()
        return None, "The verification code is incorrect."
    challenge.consumed_at = now
    return challenge, None


@auth_bp.route("/otp/request", methods=["POST"])
def request_otp():
    body = request.form if request.mimetype == "multipart/form-data" else (request.get_json(silent=True) or {})
    if request.mimetype == "multipart/form-data":
        body = request.form
    phone_number = _normalize_phone(body.get("phone_number"))
    purpose = body.get("purpose")
    if not phone_number or purpose not in {"login", "signup"}:
        return jsonify({
            "error": "A valid E.164 phone number and login or signup purpose are required.",
        }), 400

    db = get_session()
    try:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if purpose == "login" and not user:
            return jsonify({
                "message": "If this number has an account, a verification code has been sent.",
            }), 200
        if purpose == "signup":
            email = str(body.get("email") or "").strip().lower()
            full_name = str(body.get("full_name") or "").strip()
            if not email or "@" not in email or not full_name:
                return jsonify({"error": "Full name and a valid email are required."}), 400
            if user or db.query(User).filter(User.email == email).first():
                return jsonify({"error": "An account already uses that phone number or email."}), 409

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        previous = _latest_challenge(db, phone_number, purpose)
        resend_seconds = current_app.config["OTP_RESEND_SECONDS"]
        if previous and previous.created_at:
            created_at = previous.created_at.replace(tzinfo=None)
            if (now - created_at).total_seconds() < resend_seconds:
                return jsonify({"error": "Wait before requesting another code."}), 429
        hour_ago = now - timedelta(hours=1)
        recent_count = db.query(OtpChallenge).filter(
            OtpChallenge.phone_number == phone_number,
            OtpChallenge.created_at >= hour_ago,
        ).count()
        if recent_count >= current_app.config["OTP_MAX_PER_HOUR"]:
            return jsonify({"error": "Too many verification requests. Try again later."}), 429

        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge = OtpChallenge(
            phone_number=phone_number,
            purpose=purpose,
            code_hash=generate_password_hash(code),
            expires_at=now + timedelta(seconds=current_app.config["OTP_TTL_SECONDS"]),
        )
        try:
            _send_sms(phone_number, code)
        except RuntimeError as error:
            logger.warning("OTP request could not be sent: %s", error)
            return jsonify({"error": str(error)}), 503
        db.add(challenge)
        db.commit()
        return jsonify({
            "message": "Verification code sent.",
            "expires_in": current_app.config["OTP_TTL_SECONDS"],
        }), 200
    finally:
        db.close()


@auth_bp.route("/register", methods=["POST"])
def register():
    body = request.form if request.mimetype == "multipart/form-data" else (request.get_json(silent=True) or {})
    full_name = str(body.get("full_name") or "").strip()
    email = str(body.get("email") or "").strip().lower()
    phone_number = _normalize_phone(body.get("phone_number"))
    role = body.get("role", "buyer")
    national_id = str(body.get("national_id") or "").strip()
    otp = str(body.get("otp") or "")
    if (
        not full_name
        or len(full_name) > 100
        or not email
        or "@" not in email
        or len(email) > 150
        or not phone_number
        or role not in ALLOWED_REGISTRATION_ROLES
        or not national_id
        or len(national_id) > 32
        or not OTP_CODE_PATTERN.fullmatch(otp)
    ):
        return jsonify({
            "error": "Valid name, email, phone, National ID, buyer or seller role, and OTP are required.",
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
        challenge, error = _verify_challenge(db, phone_number, otp, "signup")
        if error:
            return jsonify({"error": error}), 401
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
        access_token, refresh_token = _issue_tokens(new_user)
        return jsonify({
            "user": user_schema.dump(new_user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }), 201
    except Exception:
        db.rollback()
        logger.exception("Account registration failed.")
        return jsonify({"error": "Account registration failed."}), 500
    finally:
        db.close()


@auth_bp.route("/otp/verify", methods=["POST"])
def verify_otp():
    body = request.get_json(silent=True) or {}
    phone_number = _normalize_phone(body.get("phone_number"))
    otp = str(body.get("otp") or "")
    if not phone_number or not OTP_CODE_PATTERN.fullmatch(otp):
        return jsonify({"error": "A valid phone number and six-digit code are required."}), 400

    db = get_session()
    try:
        challenge, error = _verify_challenge(db, phone_number, otp, "login")
        if error:
            return jsonify({"error": error}), 401
        user = db.query(User).filter(User.phone_number == phone_number).first()
        if not user or not user.is_verified:
            db.rollback()
            return jsonify({"error": "The account could not be verified."}), 401
        db.commit()
        access_token, refresh_token = _issue_tokens(user)
        return jsonify({
            "user": user_schema.dump(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }), 200
    finally:
        db.close()


@auth_bp.route("/login", methods=["POST"])
def login():
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

"""
utils/decorators.py
Role-based access control, layered on top of Flask-JWT-Extended.
"""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def role_required(*allowed_roles):
    """Restrict a route to specific roles using a valid JWT."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            effective_roles = {"manager", "admin"} if role == "admin" else {role}
            if not effective_roles.intersection(allowed_roles):
                return jsonify({
                    "error": "Insufficient permissions for this action",
                }), 403
            return view(*args, **kwargs)

        return wrapper

    return decorator

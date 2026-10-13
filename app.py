"""
app.py
Flask application entry point.

Run in development (SQLite, creates app.db automatically):
    python app.py
"""

import os

from dotenv import load_dotenv
from flask import Flask, request
from flask_jwt_extended import JWTManager

load_dotenv()

from config import config_by_name
from controllers import auth_bp, car_bp, deal_bp, file_bp, inquiry_bp, inspection_bp, user_bp
from database import init_db


def create_app(env=None):
    env = env or os.getenv("FLASK_ENV", "development")
    if env not in config_by_name:
        raise ValueError(f"Unknown Flask environment: {env}")

    app = Flask(__name__)
    app.config.from_object(config_by_name[env])
    if env == "production" and not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY must be configured in production.")
    if env == "production" and not app.config["JWT_SECRET_KEY"]:
        raise RuntimeError("JWT_SECRET_KEY must be configured in production.")

    JWTManager(app)
    init_db(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(car_bp)
    app.register_blueprint(inspection_bp)
    app.register_blueprint(inquiry_bp)
    app.register_blueprint(deal_bp)
    app.register_blueprint(file_bp)

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        allowed_origins = {
            configured_origin.strip().rstrip("/")
            for configured_origin in app.config["CORS_ORIGINS"]
            if configured_origin.strip()
        }
        if origin and origin.rstrip("/") in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            response.headers["Vary"] = "Origin"
        if request.path.startswith("/api/admin/documents/"):
            response.headers["Cache-Control"] = "no-store, private"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.route("/api/<path:unused_path>", methods=["OPTIONS"])
    def options_preflight(unused_path):
        return "", 204

    @app.route("/")
    def health_check():
        return {"status": "Volt Motors API is running", "environment": env}

    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Resource not found"}, 404

    @app.errorhandler(500)
    def server_error(error):
        return {"error": "Internal server error"}, 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config.get("DEBUG", True))

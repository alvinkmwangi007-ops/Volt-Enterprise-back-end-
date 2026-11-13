"""
config.py
Environment-based configuration.

- development -> SQLite file app.db (zero setup, good for local dev)
- production  -> MySQL (volt_motors), same DB you created earlier
- testing     -> in-memory SQLite (fast, isolated test runs)

Select which one loads via the FLASK_ENV environment variable.
"""

import os
import tempfile
from datetime import timedelta


basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    PRIVATE_UPLOAD_FOLDER = os.getenv(
        "PRIVATE_UPLOAD_FOLDER",
        os.path.join(tempfile.gettempdir(), "volt-enterprise-private-uploads"),
    )
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "volt-motors-98ea6")
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    INSPECTION_PARTNER_API_KEY = os.getenv(
        "INSPECTION_PARTNER_API_KEY",
        "change-this-partner-key",
    )


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = Config.SECRET_KEY or "volt-local-development-secret-only-123"
    JWT_SECRET_KEY = Config.JWT_SECRET_KEY or "volt-local-development-jwt-secret-123"
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DEV_DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'app.db')}",
    )


class ProductionConfig(Config):
    DEBUG = False
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "volt_motors")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    )


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "volt-testing-secret-key-32-bytes-minimum"
    JWT_SECRET_KEY = "volt-testing-jwt-key-32-bytes-minimum"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

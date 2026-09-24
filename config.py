"""
config.py
Environment-based configuration.

- development -> SQLite file app.db (zero setup, good for local dev)
- production  -> MySQL (volt_motors), same DB you created earlier
- testing     -> in-memory SQLite (fast, isolated test runs)

Select which one loads via the FLASK_ENV environment variable.
"""

import os
from datetime import timedelta


basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-jwt-secret-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    INSPECTION_PARTNER_API_KEY = os.getenv(
        "INSPECTION_PARTNER_API_KEY",
        "change-this-partner-key",
    )


class DevelopmentConfig(Config):
    DEBUG = True
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
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

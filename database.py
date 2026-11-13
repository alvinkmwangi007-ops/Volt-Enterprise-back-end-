"""
database.py
Database setup. init_db(app) must be called once from the app factory
(app.py) before any request uses get_session().
"""

import time

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

_engine = None
_SessionFactory = None


def init_db(app):
    """Create the engine/session factory and create missing tables."""
    global _engine, _SessionFactory

    _engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        pool_pre_ping=True,
        pool_recycle=280,
    )
    _SessionFactory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine,
    )

    import Models  # noqa: F401: register every ORM model with Base.metadata

    for attempt in range(30):
        try:
            with _engine.connect():
                break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)

    _migrate_existing_columns(_engine)
    Base.metadata.create_all(bind=_engine)


def _migrate_existing_columns(engine):
    """Add marketplace columns without deleting existing user or car records."""
    existing_tables = inspect(engine).get_table_names()
    additions = {
        "users": {
            "national_id": "VARCHAR(32)",
            "interest_notifications": "BOOLEAN NOT NULL DEFAULT 0",
        },
        "cars": {
            "plate": "VARCHAR(16)",
            "vehicle_type": "VARCHAR(60)",
            "showroom": "VARCHAR(120)",
            "online_sale": "BOOLEAN NOT NULL DEFAULT 0",
            "finance_status": "VARCHAR(32)",
            "imported_vehicle": "BOOLEAN",
        },
    }
    with engine.begin() as connection:
        if "cars" in existing_tables:
            existing_indexes = {index["name"] for index in inspect(connection).get_indexes("cars")}
            if "ix_cars_status" not in existing_indexes:
                connection.execute(text("CREATE INDEX ix_cars_status ON cars (status)"))
        if engine.dialect.name == "mysql" and "users" in existing_tables:
            connection.execute(text(
                "ALTER TABLE users MODIFY COLUMN role "
                "ENUM('buyer', 'seller', 'manager', 'admin') NOT NULL"
            ))
        for table, columns in additions.items():
            if table not in existing_tables:
                continue
            existing_columns = {
                column["name"] for column in inspect(connection).get_columns(table)
            }
            for column, definition in columns.items():
                if column not in existing_columns:
                    quoted_table = connection.dialect.identifier_preparer.quote(table)
                    quoted_column = connection.dialect.identifier_preparer.quote(column)
                    connection.execute(text(
                        f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {definition}"
                    ))


def get_session():
    """Return a new database session."""
    if _SessionFactory is None:
        raise RuntimeError("Database not initialized. Call init_db(app) first.")
    return _SessionFactory()


def SessionLocal():
    """Backward-compatible session factory used by existing controllers."""
    return get_session()

"""
database.py
Database setup. init_db(app) must be called once from the app factory
(app.py) before any request uses get_session().
"""

from sqlalchemy import create_engine
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
    )
    _SessionFactory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine,
    )

    import Models  # noqa: F401: register every ORM model with Base.metadata

    Base.metadata.create_all(bind=_engine)


def get_session():
    """Return a new database session."""
    if _SessionFactory is None:
        raise RuntimeError("Database not initialized. Call init_db(app) first.")
    return _SessionFactory()


def SessionLocal():
    """Backward-compatible session factory used by existing controllers."""
    return get_session()

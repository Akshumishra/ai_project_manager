<<<<<<< HEAD
from __future__ import annotations

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models (SQLAlchemy 2.0+ style)."""

    pass


# ── Lazy engine/session factory ───────────────────────────────────────────────
# Nothing is created here at import time.  _engine and _SessionLocal are
# populated by _get_session_local() on first call.

_engine = None
_SessionLocal: sessionmaker | None = None


def _get_database_url() -> str:
    """
    Resolve DATABASE_URL from centralized configuration framework.
    """
    from src.backend.config import settings

    url = settings.DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Add it to your .env file before starting the application."
        )
    return url


def _get_session_local() -> sessionmaker:
    """Return the module-level sessionmaker, creating the engine on first call."""
    global _engine, _SessionLocal  # noqa: PLW0603
    if _SessionLocal is None:
        _engine = create_engine(
            _get_database_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
        )
        _SessionLocal = sessionmaker(
            bind=_engine, autocommit=False, autoflush=False
        )
        logger.info("Database engine initialized (pool_size=5, max_overflow=10).")
    return _SessionLocal


# Public alias — existing callers that do `from ... import SessionLocal` still work.
# The object itself is the sessionmaker; calling it produces a Session.
def get_session_local() -> sessionmaker:
    """Public accessor for the shared sessionmaker singleton."""
    return _get_session_local()
=======
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.backend.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
>>>>>>> af8dd30d58119a11f2c37c2545e22d54abe63d01


def get_db():
    """
    FastAPI dependency: yield a DB session and close it after the request.

    Usage::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    factory = _get_session_local()
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all registered tables.  Use Alembic migrations in production."""
    factory = _get_session_local()
    Base.metadata.create_all(bind=factory.kw["bind"])

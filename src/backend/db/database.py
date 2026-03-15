"""
src.backend.db.database
~~~~~~~~~~~~~~~~~~~~~~~

SQLAlchemy engine, session factory, and FastAPI dependency.

The engine is created **lazily** on first use (not at module import time).
This lets any module safely import ``Base``, ``get_db``, or ``SessionLocal``
without immediately requiring DATABASE_URL to be set — which is critical for
the meeting_bot subprocess and for test environments that patch the URL.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()

# ── Lazy engine/session factory ───────────────────────────────────────────────
# Nothing is created here at import time.  _engine and _SessionLocal are
# populated by _get_session_local() on first call.

_engine = None
_SessionLocal: sessionmaker | None = None


def _get_database_url() -> str:
    """
    Resolve DATABASE_URL from environment.

    Checks the environment directly (not via src.backend.config.Config) so
    this module remains importable in any subprocess regardless of whether
    the wider backend config is available.
    """
    url = os.environ.get("DATABASE_URL")
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
        _engine = create_engine(_get_database_url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(
            bind=_engine, autocommit=False, autoflush=False
        )
    return _SessionLocal


# Public alias — existing callers that do `from ... import SessionLocal` still work.
# The object itself is the sessionmaker; calling it produces a Session.
def get_session_local() -> sessionmaker:
    """Public accessor for the shared sessionmaker singleton."""
    return _get_session_local()


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

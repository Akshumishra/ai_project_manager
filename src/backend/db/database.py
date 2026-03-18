from __future__ import annotations

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from src.backend.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models (SQLAlchemy 2.0+ style)."""

    pass


# ── Public Database Objects ───────────────────────────────────────────────────
# Instantiated eagerly on import; compatible with standard FastAPI lookups.

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False
)


def get_session_local() -> sessionmaker:
    """Public accessor for backwards compatibility."""
    return SessionLocal


def get_db():
    """
    FastAPI dependency: yield a DB session and close it after the request.

    Usage::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all registered tables.  Use Alembic migrations in production."""
    Base.metadata.create_all(bind=engine)

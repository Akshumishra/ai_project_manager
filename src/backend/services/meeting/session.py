import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from src.backend.db.database import get_session_local
from src.backend.model.meeting import Meeting

logger = logging.getLogger(__name__)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Yield a transactional DB session; rolls back on error, always closes."""
    factory = get_session_local()
    db: Session = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_meeting_by_session(db: Session, bot_session_id: str) -> Meeting | None:
    """Fetch a Meeting by its bot_session_id within an open session."""
    return db.query(Meeting).filter(Meeting.bot_session_id == bot_session_id).first()

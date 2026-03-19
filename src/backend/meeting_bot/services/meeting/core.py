import logging
from datetime import datetime, timezone
from uuid import UUID

from src.backend.model.meeting import Meeting, MeetingStatus, MeetingType
from src.backend.meeting_bot.services.meeting.session import get_db_session, get_meeting_by_session

logger = logging.getLogger(__name__)

def create_meeting(
    *,
    project_id: UUID,
    created_by: UUID,
    title: str,
    meet_url: str,
    bot_session_id: str,
    meeting_type: MeetingType = MeetingType.AD_HOC,
    task_id: UUID | None = None,
    agenda: str | None = None,
    scheduled_at: datetime | None = None,
    scheduled_meeting_id: UUID | None = None,
) -> UUID:
    """
    Persist a new Meeting row or update an existing scheduled meeting.
    """
    with get_db_session() as db:
        if scheduled_meeting_id:
             meeting = db.query(Meeting).filter(Meeting.id == scheduled_meeting_id).first()
             if meeting:
                  meeting.bot_session_id = bot_session_id
                  logger.info("Picked up scheduled meeting: id=%s new_bot_session=%s", meeting.id, bot_session_id)
                  return meeting.id

        meeting = Meeting(
            project_id=project_id,
            created_by=created_by,
            title=title,
            meet_url=meet_url,
            bot_session_id=bot_session_id,
            meeting_type=meeting_type,
            status=MeetingStatus.SCHEDULED,
            task_id=task_id,
            agenda=agenda,
            scheduled_at=scheduled_at or datetime.now(timezone.utc),
        )
        db.add(meeting)
        db.flush()  # Populate meeting.id before commit.
        meeting_id = meeting.id

    logger.info("Meeting created: id=%s bot_session=%s", meeting_id, bot_session_id)
    return meeting_id


def mark_meeting_started(bot_session_id: str) -> None:
    """Flip status → IN_PROGRESS and record the actual start timestamp."""
    with get_db_session() as db:
        meeting = get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("mark_meeting_started: no row for bot_session=%s", bot_session_id)
            return
        meeting.status = MeetingStatus.IN_PROGRESS
        meeting.started_at = datetime.now(timezone.utc)
    logger.info("Meeting started: bot_session=%s", bot_session_id)


def mark_meeting_ended(bot_session_id: str) -> None:
    """Flip status → COMPLETED and record the actual end timestamp."""
    with get_db_session() as db:
        meeting = get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("mark_meeting_ended: no row for bot_session=%s", bot_session_id)
            return
        meeting.status = MeetingStatus.COMPLETED
        meeting.ended_at = datetime.now(timezone.utc)
    logger.info("Meeting ended: bot_session=%s", bot_session_id)


def mark_meeting_cancelled(bot_session_id: str) -> None:
    """Flip status → CANCELLED."""
    with get_db_session() as db:
        meeting = get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("mark_meeting_cancelled: no row for bot_session=%s", bot_session_id)
            return
        meeting.status = MeetingStatus.CANCELLED
        meeting.ended_at = datetime.now(timezone.utc)
    logger.info("Meeting cancelled: bot_session=%s", bot_session_id)

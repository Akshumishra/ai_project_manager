from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from src.backend.model.meeting import Meeting, MeetingStatus, MeetingType
from src.backend.meeting_bot.services.meeting.session import (
    get_db_session,
    get_meeting_by_session,
)
from src.backend.meeting_bot.constants import (
    DEFAULT_MEETING_DURATION_MINS,
    SCHEDULE_MEETING_OFFSET_MINS,
    BOT_SESSION_ID_PREFIX,
)

logger = logging.getLogger(__name__)


async def schedule_meeting(
    project_id: UUID,
    created_by: UUID,
    title: str,
    agenda: str | None = None,
    duration_minutes: int = DEFAULT_MEETING_DURATION_MINS,
    task_id: UUID | None = None,
) -> tuple[UUID, str]:
    """
    Coordination layer that schedules a meeting via Google Calendar and persists it to the DB.

    This centralizes the meeting creation flow for both Slack and API callers.
    """
    from src.backend.meeting_bot.services.calendar_service import create_calendar_meet

    ist = ZoneInfo("Asia/Kolkata")
    scheduled_at_dt = datetime.now(ist) + timedelta(
        minutes=SCHEDULE_MEETING_OFFSET_MINS
    )

    meet_url, _ = await asyncio.to_thread(
        create_calendar_meet,
        title=title,
        scheduled_at=scheduled_at_dt,
        duration_minutes=duration_minutes,
    )

    if not meet_url:
        raise RuntimeError("Google Calendar failed to generate a Meet link.")

    bot_session_id = f"{BOT_SESSION_ID_PREFIX}{uuid.uuid4().hex[:8]}"
    meeting_id = await asyncio.to_thread(
        create_meeting,
        project_id=project_id,
        created_by=created_by,
        title=title,
        meet_url=meet_url,
        bot_session_id=bot_session_id,
        task_id=task_id,
        agenda=agenda,
        scheduled_at=scheduled_at_dt,
    )

    return meeting_id, meet_url


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
            meeting = (
                db.query(Meeting).filter(Meeting.id == scheduled_meeting_id).first()
            )
            if meeting:
                meeting.bot_session_id = bot_session_id
                logger.info(
                    "Picked up scheduled meeting: id=%s new_bot_session=%s",
                    meeting.id,
                    bot_session_id,
                )
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
        db.flush()
        meeting_id = meeting.id

    logger.info("Meeting created: id=%s bot_session=%s", meeting_id, bot_session_id)
    return meeting_id


def mark_meeting_ended(bot_session_id: str) -> None:
    """Flip status → COMPLETED and record the actual end timestamp."""
    with get_db_session() as db:
        meeting = get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning(
                "mark_meeting_ended: no row for bot_session=%s", bot_session_id
            )
            return
        meeting.status = MeetingStatus.COMPLETED
        meeting.ended_at = datetime.now(timezone.utc)
    logger.info("Meeting ended: bot_session=%s", bot_session_id)

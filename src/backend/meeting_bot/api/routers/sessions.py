from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, status

from src.backend.meeting_bot.api.schemas import (
    ScheduleCalendarMeetingRequest,
    ScheduleCalendarMeetingResponse,
)
from src.backend.meeting_bot.services.calendar_service import create_calendar_meet
from src.backend.meeting_bot.services.meeting import create_meeting
from src.backend.meeting_bot.constants import (
    IST_TIMEZONE_OFFSET_HOURS,
    IST_TIMEZONE_OFFSET_MINS,
    SCHEDULE_MEETING_OFFSET_MINS,
    BOT_SESSION_ID_PREFIX
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Sessions"])


@router.get("/")
async def root() -> dict:
    """Health-check endpoint."""
    return {"message": "Google Meet Calendar Scheduler API is running."}


@router.post(
    "/sessions/schedule-calendar",
    response_model=ScheduleCalendarMeetingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def schedule_meeting_calendar(
    request: ScheduleCalendarMeetingRequest,
) -> dict:
    """
    Schedule a meeting in Google Calendar, generate an unlocked Meet link,
    and persist it in our database.

    Because Fireflies automations auto-join Calendar items, no manual
    invocation is required.
    """
    # ── 1. Calculate the scheduled datetime (5 mins from now in IST) ────────
    ist = timezone(timedelta(hours=IST_TIMEZONE_OFFSET_HOURS, minutes=IST_TIMEZONE_OFFSET_MINS))
    scheduled_at_dt = datetime.now(ist) + timedelta(minutes=SCHEDULE_MEETING_OFFSET_MINS)

    # ── 2. Generate Google Meet space via Calendar API ──────────────────────
    try:
        meet_url, event_response = await asyncio.to_thread(
            create_calendar_meet,
            title=request.title,
            scheduled_at=scheduled_at_dt,
            duration_minutes=request.duration_minutes,
        )
    except Exception:
        logger.exception("Google Calendar Meet generation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate Google Meet link. Please try again later.",
        )

    if not meet_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google Calendar created the event but failed to generate a video link.",
        )

    # ── 3. Persist Meeting to DB ───────────────────────────────────────────
    bot_session_id = f"{BOT_SESSION_ID_PREFIX}{uuid.uuid4().hex[:8]}"

    try:
        meeting_id = await asyncio.to_thread(
            create_meeting,
            project_id=request.project_id,
            created_by=request.created_by,
            title=request.title,
            meet_url=meet_url,
            bot_session_id=bot_session_id,
            task_id=request.task_id,
            agenda=request.agenda,
            scheduled_at=scheduled_at_dt,
        )
    except Exception:
        logger.exception("Database Meeting persistence failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist scheduled meeting. Please contact support.",
        )

    return {
        "meeting_id": meeting_id,
        "meet_url": meet_url,
        "message": "Google Calendar meeting created and saved in database successfully.",
    }

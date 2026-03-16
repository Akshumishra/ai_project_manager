from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from meeting_bot.api.schemas import (
    ScheduleCalendarMeetingRequest,
    ScheduleCalendarMeetingResponse,
)
from src.backend.services.ai.processor import infer_meeting_participants
from src.backend.services.calendar_service import create_calendar_meet
from src.backend.services.meeting import add_participants, create_meeting

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Sessions"])


@router.get("/")
async def root() -> dict:
    """Health-check endpoint."""
    return {"message": "Google Meet Calendar Scheduler API is running."}


@router.post(
    "/sessions/schedule-calendar",
    response_model=ScheduleCalendarMeetingResponse,
    status_code=201,
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
    # ── 1. Parse and validate the scheduled datetime ────────────────────────
    try:
        scheduled_at_dt = datetime.fromisoformat(request.scheduled_at)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="scheduled_at must be a valid ISO-8601 datetime string.",
        )

    if scheduled_at_dt.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="scheduled_at must include timezone information (e.g. '+05:30' or 'Z').",
        )

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
            status_code=502,
            detail="Failed to generate Google Meet link. Please try again later.",
        )

    if not meet_url:
        raise HTTPException(
            status_code=502,
            detail="Google Calendar created the event but failed to generate a video link.",
        )

    # ── 3. Infer participants via AI LLM agent ─────────────────────────────
    inferred: list[dict] = []
    try:
        inferred = await asyncio.to_thread(
            infer_meeting_participants,
            str(request.project_id),
            request.agenda,
        )
    except Exception:
        logger.exception("AI Participant inference failed — continuing without suggestions")

    # ── 4. Persist Meeting to DB ───────────────────────────────────────────
    bot_session_id = f"ffl-{uuid.uuid4().hex[:8]}"

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
            status_code=500,
            detail="Failed to persist scheduled meeting. Please contact support.",
        )

    # ── 5. Save participants into DB ───────────────────────────────────────
    if inferred:
        try:
            participants_data = [
                {
                    "project_member_id": uuid.UUID(p["project_member_id"]),
                    "invite_reason": p.get("reason", ""),
                    "invite_source": "AI_SUGGESTED",
                    "role_in_meeting": p.get("role_in_meeting", "ATTENDEE"),
                }
                for p in inferred
            ]
            await asyncio.to_thread(
                add_participants, bot_session_id, participants_data
            )
        except Exception:
            logger.exception("Database Participant persistence failed")

    return {
        "meeting_id": meeting_id,
        "meet_url": meet_url,
        "message": "Google Calendar meeting created and saved in database successfully.",
        "inferred_participants": inferred,
    }

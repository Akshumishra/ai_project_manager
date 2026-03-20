from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from src.backend.meeting_bot.api.schemas import (
    ScheduleCalendarMeetingRequest,
    ScheduleCalendarMeetingResponse,
)
from src.backend.meeting_bot.services.meeting import schedule_meeting

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
    API facade for scheduling a meeting.
    Hands off all business logic to schedule_meeting.
    """
    try:
        meeting_id, meet_url = await schedule_meeting(
            project_id=request.project_id,
            created_by=request.created_by,
            title=request.title,
            agenda=request.agenda,
            duration_minutes=request.duration_minutes,
            task_id=request.task_id,
        )
        
        return {
            "meeting_id": meeting_id,
            "meet_url": meet_url,
            "message": "Google Calendar meeting created and saved in database successfully.",
        }

    except RuntimeError as exc:
        logger.error("Meeting orchestration failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception:
        logger.exception("Unexpected failure during meeting scheduling")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please contact support.",
        )

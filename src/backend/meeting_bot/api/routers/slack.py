import asyncio
import logging
import httpx
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from src.backend.db.database import get_db
from src.backend.model.project import ProjectSlackDetail, ProjectMember
from src.backend.meeting_bot.api.schemas import ScheduleCalendarMeetingRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Slack"])


async def schedule_and_notify_slack(
    response_url: str,
    request_wrapper: ScheduleCalendarMeetingRequest,
    title: str,
    duration_minutes: int,
    agenda: str,
):
    """Background task to schedule the meeting and notify Slack via response_url."""
    try:
        from src.backend.meeting_bot.api.routers.sessions import schedule_meeting_calendar

        response_dict = await schedule_meeting_calendar(request=request_wrapper)
        meet_url = response_dict.get("meet_url", "https://meet.google.com")

        # Broadcast the success back to the entire channel
        payload = {
            "response_type": "in_channel",
            "replace_original": "true",
            "text": (
                f"✅  *Google Meet Space Scheduled!*\n"
                f"📅  **Title**: {title}\n"
                f"⏳  **Duration**: {duration_minutes} minutes\n"
                f"🔗  **Join link**: {meet_url}\n"
                f"📝  **Agenda**: {agenda or 'None provided.'}"
            ),
        }

        async with httpx.AsyncClient() as client:
            await client.post(response_url, json=payload)

    except Exception as exc:
        logger.exception("Slack background scheduler failed")
        async with httpx.AsyncClient() as client:
            await client.post(
                response_url, 
                json={"response_type": "ephemeral", "text": f"🚨  Scheduling failed: {exc}"}
            )


@router.post("/slack/meet", status_code=status.HTTP_200_OK)
async def slack_meeting_command(
    background_tasks: BackgroundTasks,
    channel_id: str = Form(...),
    user_id: str = Form(...),
    response_url: str = Form(...),
    text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> dict:
    """
    Slack Slash Command handler for scheduling a Google Calendar meeting.

    Usage: /meet [duration] [title] [agenda]
    Example: /meet 45 standup Daily sync and standup updates
    """
    logger.info("Slack slash command received from channel=%s user=%s", channel_id, user_id)

    # ── 1. Parse duration, title, and agenda ──────────────────────────────
    duration_minutes = 45
    title = "Scheduled Meeting"
    agenda = ""

    if text:
        parts = text.strip().split(" ", 2)
        if len(parts) > 0:
            try:
                # Try to parse first part as duration
                duration_minutes = int(parts[0])
                if len(parts) > 1:
                    title = parts[1]
                if len(parts) > 2:
                    agenda = parts[2]
            except ValueError:
                # First part is NOT a number; treat whole text as title + agenda
                split_text = text.strip().split(" ", 1)
                title = split_text[0]
                agenda = split_text[1] if len(split_text) > 1 else ""

    if duration_minutes < 5:
        duration_minutes = 5
    if duration_minutes > 480:
        duration_minutes = 480

    # ── 2. Database Lookup ──────────────────────────────────────────────────
    try:
        slack_channel_map = (
            db.query(ProjectSlackDetail)
            .filter(ProjectSlackDetail.channel_id == channel_id)
            .first()
        )

        if not slack_channel_map:
            logger.warning("Slack channel %s not mapped to any project", channel_id)
            return {
                "response_type": "ephemeral",
                "text": f"This Slack channel (ID: `{channel_id}`) is not connected to any project dashboard. Please configure the app integration first.",
            }

        project_id = slack_channel_map.project_id

        member_map = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.slack_id == user_id,
            )
            .first()
        )

        if not member_map:
            logger.warning("Slack user %s not found in project %s member list", user_id, project_id)
            return {
                "response_type": "ephemeral",
                "text": f"Your Slack ID (`{user_id}`) is not in this project's member list. Please contact your administrator.",
            }

        created_by_uuid = member_map.user_id

    except Exception:
        logger.exception("Slack resolver DB lookup failed")
        return {
            "response_type": "ephemeral",
            "text": "Database lookup error. Please try again later.",
        }

    # ── 3. Queue scheduling task ───────────────────────────────────────────
    request_wrapper = ScheduleCalendarMeetingRequest(
        project_id=project_id,
        created_by=created_by_uuid,
        title=title,
        agenda=agenda,
        duration_minutes=duration_minutes,
    )

    # Trigger async background task to defer downstream calendar blocking times
    background_tasks.add_task(
        schedule_and_notify_slack,
        response_url,
        request_wrapper,
        title,
        duration_minutes,
        agenda,
    )

    return {
        "response_type": "ephemeral",
        "text": "⏳  **Scheduling meeting, please hold...**",
    }

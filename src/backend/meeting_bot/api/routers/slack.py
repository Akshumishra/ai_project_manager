import asyncio
import logging
import httpx
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.backend.db.database import get_db, SessionLocal
from src.backend.model.project import ProjectSlackDetail, ProjectMember
from src.backend.meeting_bot.api.schemas import ScheduleCalendarMeetingRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Slack"])


async def schedule_and_notify_slack(
    channel_id: str,
    user_id: str,
    response_url: str,
    text_input: Optional[str],
):
    """Background task to resolve project details, schedule the meeting, and notify Slack."""
    from src.backend.meeting_bot.api.routers.sessions import schedule_meeting_calendar

    db = SessionLocal()
    try:
        # ── 1. Parse duration, title, and agenda ──────────────────────────────
        duration_minutes = 45
        title = "Scheduled Meeting"
        agenda = ""

        if text_input:
            parts = text_input.strip().split(" ", 2)
            if len(parts) > 0:
                try:
                    duration_minutes = int(parts[0])
                    if len(parts) > 1:
                        title = parts[1]
                    if len(parts) > 2:
                        agenda = parts[2]
                except ValueError:
                    split_text = text_input.strip().split(" ", 1)
                    title = split_text[0]
                    agenda = split_text[1] if len(split_text) > 1 else ""

        if duration_minutes < 5:
            duration_minutes = 5
        if duration_minutes > 480:
            duration_minutes = 480

        # ── 2. Database Lookup ──────────────────────────────────────────────────
        # Lookup project for the channel
        slack_channel_map = (
            db.query(ProjectSlackDetail)
            .filter(ProjectSlackDetail.channel_id == channel_id)
            .first()
        )

        if not slack_channel_map:
            logger.warning("Slack channel %s not mapped to any project", channel_id)
            async with httpx.AsyncClient() as client:
                await client.post(
                    response_url,
                    json={
                        "response_type": "ephemeral",
                        "text": f"This Slack channel (ID: `{channel_id}`) is not connected to any project dashboard. Please configure the app integration first.",
                    }
                )
            return

        project_id = slack_channel_map.project_id

        # ── 3. RLS Context & Member Lookup ────────────────────────────────────
        # SET LOCAL app.project_id is required for RLS policies
        db.execute(
            text("SET LOCAL app.project_id = :project_id"),
            {"project_id": str(project_id)}
        )

        member_map = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.slack_id == user_id,
            )
            .first()
        )

        if not member_map:
            logger.warning("Slack user %s not found in project %s member list (RLS active)", user_id, project_id)
            async with httpx.AsyncClient() as client:
                await client.post(
                    response_url,
                    json={
                        "response_type": "ephemeral",
                        "text": f"Your Slack ID (`{user_id}`) is not in this project's member list. Please contact your administrator.",
                    }
                )
            return

        created_by_uuid = member_map.user_id

        # ── 4. Schedule Meeting ───────────────────────────────────────────────
        request_wrapper = ScheduleCalendarMeetingRequest(
            project_id=project_id,
            created_by=created_by_uuid,
            title=title,
            agenda=agenda or "",
            duration_minutes=duration_minutes,
        )

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
    finally:
        db.close()


@router.post("/slack/meet", status_code=status.HTTP_200_OK)
async def slack_meeting_command(
    background_tasks: BackgroundTasks,
    channel_id: str = Form(...),
    user_id: str = Form(...),
    response_url: str = Form(...),
    text: Optional[str] = Form(None),
) -> dict:
    """
    Slack Slash Command handler for scheduling a Google Calendar meeting.
    Acknowledges immediately to avoid Slack timeouts.
    """
    logger.info("Slack slash command received (async) from channel=%s user=%s", channel_id, user_id)

    background_tasks.add_task(
        schedule_and_notify_slack,
        channel_id,
        user_id,
        response_url,
        text,
    )

    return {
        "response_type": "ephemeral",
        "text": "⏳  **Scheduling meeting, please hold...**",
    }

import logging
import httpx
from typing import Optional

from fastapi import APIRouter, Form, status, BackgroundTasks

from src.backend.db.database import SessionLocal
from src.backend.model.project import ProjectSlackDetail, ProjectMember
from src.backend.meeting_bot.api.schemas import ScheduleCalendarMeetingRequest
from src.backend.meeting_bot.constants import (
    DEFAULT_MEETING_DURATION_MINS,
    MIN_MEETING_DURATION_MINS,
    MAX_MEETING_DURATION_MINS,
    DEFAULT_MEET_URL,
    SLACK_MEETING_SUCCESS_TEMPLATE,
    SLACK_MEET_EPHEMERAL_SCHEDULING_MSG
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Slack"])


async def _send_slack_ephemeral_message(response_url: str, text_msg: str) -> None:
    """Helper to send a quick ephemeral message to Slack."""
    async with httpx.AsyncClient() as client:
        await client.post(
            response_url,
            json={
                "response_type": "ephemeral",
                "text": text_msg,
            }
        )


def _parse_slack_command_text(text_input: Optional[str]) -> tuple[int, str, str]:
    """Parse duration, title, and agenda with direct partitioning and indexing."""
    parts = (text_input or "").strip().split(None, 2)

    duration_raw = parts[0] if len(parts) > 0 else str(DEFAULT_MEETING_DURATION_MINS)
    title = parts[1] if len(parts) > 1 else "Scheduled Meeting"
    agenda = parts[2] if len(parts) > 2 else ""

    duration = (
        int(duration_raw) if duration_raw.isdigit() else DEFAULT_MEETING_DURATION_MINS
    )

    duration = max(MIN_MEETING_DURATION_MINS, min(duration, MAX_MEETING_DURATION_MINS))
    return duration, title, agenda


async def schedule_and_notify_slack(
    channel_id: str,
    user_id: str,
    response_url: str,
    text_input: Optional[str],
):
    """Background task to resolve project details, schedule the meeting, and notify Slack."""
    from src.backend.meeting_bot.services.meeting import schedule_meeting

    db = SessionLocal()
    try:
        # ── 1. Parse duration, title, and agenda ──────────────────────────────
        duration_minutes, title, agenda = _parse_slack_command_text(text_input)

        # ── 2. Database Lookup ──────────────────────────────────────────────────
        # Lookup project for the channel
        slack_channel_map = (
            db.query(ProjectSlackDetail)
            .filter(ProjectSlackDetail.channel_id == channel_id)
            .first()
        )

        if not slack_channel_map:
            logger.warning("Slack channel %s not mapped to any project", channel_id)
            await _send_slack_ephemeral_message(
                response_url,
                f"This Slack channel (ID: `{channel_id}`) is not connected to any project dashboard. Please configure the app integration first.",
            )
            return

        project_id = slack_channel_map.project_id

        # ── 3. Member Lookup ──────────────────────────────────────────────────
        member_map = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.slack_id == user_id,
            )
            .first()
        )

        if not member_map:
            logger.warning(
                "Slack user %s not found in project %s member list", user_id, project_id
            )
            await _send_slack_ephemeral_message(
                response_url,
                f"Your Slack ID (`{user_id}`) is not in this project's member list. Please contact your administrator.",
            )
            return

        created_by_uuid = member_map.user_id

        # ── 4. Orchestrate Meeting Scheduling ───────────────────────────────
        _, meet_url = await schedule_meeting(
            project_id=project_id,
            created_by=created_by_uuid,
            title=title,
            agenda=agenda or "",
            duration_minutes=duration_minutes,
        )

        # Broadcast the success back to the entire channel
        message_text = SLACK_MEETING_SUCCESS_TEMPLATE.format(
            title=title,
            duration_minutes=duration_minutes,
            meet_url=meet_url,
            agenda=agenda or "None provided.",
        )
        payload = {
            "response_type": "in_channel",
            "replace_original": "true",
            "text": message_text,
        }

        async with httpx.AsyncClient() as client:
            await client.post(response_url, json=payload)

    except Exception as exc:
        logger.exception("Slack background scheduler failed")
        await _send_slack_ephemeral_message(
            response_url, f"🚨  Scheduling failed: {exc}"
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
    logger.info(
        "Slack slash command received (async) from channel=%s user=%s",
        channel_id,
        user_id,
    )

    background_tasks.add_task(
        schedule_and_notify_slack,
        channel_id,
        user_id,
        response_url,
        text,
    )

    return {
        "response_type": "ephemeral",
        "text": SLACK_MEET_EPHEMERAL_SCHEDULING_MSG,
    }

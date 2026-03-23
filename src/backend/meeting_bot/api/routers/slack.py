import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Form, status

from src.backend.db.database import SessionLocal
from src.backend.meeting_bot.constants import (
    DEFAULT_MEETING_DURATION_MINS,
    MAX_MEETING_DURATION_MINS,
    MIN_MEETING_DURATION_MINS,
    SLACK_MEET_EPHEMERAL_SCHEDULING_MSG,
)
from src.backend.meeting_bot.services.slack_notification import SlackMeetingCoordinator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Slack"])


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


async def process_slack_meeting_request(
    channel_id: str,
    user_id: str,
    response_url: str,
    text_input: Optional[str],
):
    """Background task wrapper that uses the SlackMeetingCoordinator service."""
    from src.backend.meeting_bot.services.meeting import schedule_meeting

    db = SessionLocal()
    coordinator = SlackMeetingCoordinator(db, response_url)

    try:
        duration_mins, title, agenda = _parse_slack_command_text(text_input)

        channel_config = coordinator.get_project_details(channel_id)
        if not channel_config:
            await coordinator.send_ephemeral(
                f"This Slack channel (ID: `{channel_id}`) is not connected to any project dashboard."
            )
            return

        project_id = channel_config.project_id

        creator_record = coordinator.get_creator_identity(project_id, user_id)
        if not creator_record:
            await coordinator.send_ephemeral(
                f"Your Slack ID (`{user_id}`) is not in this project's member list."
            )
            return

        _, meet_url = await schedule_meeting(
            project_id=project_id,
            created_by=creator_record.user_id,
            title=title,
            agenda=agenda or "",
            duration_minutes=duration_mins,
        )

        await coordinator.broadcast_success(title, duration_mins, meet_url, agenda)

    except Exception as exc:
        logger.exception("Slack background scheduler failed")
        await coordinator.send_ephemeral(f"🚨  Scheduling failed: {exc}")
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
    """Slack Slash Command handler for scheduling a Google Calendar meeting."""
    logger.info(
        "Slack slash command received (async) from channel=%s user=%s",
        channel_id,
        user_id,
    )

    background_tasks.add_task(
        process_slack_meeting_request,
        channel_id,
        user_id,
        response_url,
        text,
    )

    return {
        "response_type": "ephemeral",
        "text": SLACK_MEET_EPHEMERAL_SCHEDULING_MSG,
    }

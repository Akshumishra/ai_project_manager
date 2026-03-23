import json
import logging
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.backend.config import settings
from src.backend.meeting_bot.constants import (
    SLACK_BLOCK_TEXT_MRKDWN,
    SLACK_BLOCK_TEXT_PLAIN,
    SLACK_BLOCK_TYPE_CONTEXT,
    SLACK_BLOCK_TYPE_DIVIDER,
    SLACK_BLOCK_TYPE_HEADER,
    SLACK_BLOCK_TYPE_SECTION,
    SLACK_MEETING_SUCCESS_TEMPLATE,
)
from src.backend.meeting_bot.services.meeting.session import get_db_session
from src.backend.model.project import ProjectMember, ProjectSlackDetail

logger = logging.getLogger(__name__)


class SlackMeetingCoordinator:
    """Orchestrates meeting creation and notification flows specifically for Slack."""

    def __init__(self, db: Session, response_url: str):
        self.db = db
        self.response_url = response_url

    async def send_ephemeral(self, text_msg: str) -> None:
        """Helper to send a quick ephemeral message to Slack."""
        async with httpx.AsyncClient() as client:
            await client.post(
                self.response_url,
                json={
                    "response_type": "ephemeral",
                    "text": text_msg,
                },
            )

    async def broadcast_success(
        self, title: str, duration: int, meet_url: str, agenda: Optional[str]
    ) -> None:
        """Broadcast the success back to the entire channel."""
        message_text = SLACK_MEETING_SUCCESS_TEMPLATE.format(
            title=title,
            duration_minutes=duration,
            meet_url=meet_url,
            agenda=agenda or "None provided.",
        )
        payload = {
            "response_type": "in_channel",
            "replace_original": "true",
            "text": message_text,
        }
        async with httpx.AsyncClient() as client:
            await client.post(self.response_url, json=payload)

    def get_project_details(self, channel_id: str) -> Optional[ProjectSlackDetail]:
        """Lookup project details for the given Slack channel."""
        details = (
            self.db.query(ProjectSlackDetail)
            .filter(ProjectSlackDetail.channel_id == channel_id)
            .first()
        )
        if not details:
            logger.warning("Slack channel %s not mapped to any project", channel_id)
        return details

    def get_creator_identity(
        self, project_id: str, user_id: str
    ) -> Optional[ProjectMember]:
        """Lookup member details and set RLS context."""
        self.db.execute(
            text("SET LOCAL app.project_id = :project_id"),
            {"project_id": str(project_id)},
        )

        member = (
            self.db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.slack_id == user_id,
            )
            .first()
        )
        if not member:
            logger.warning(
                "Slack user %s not found in project %s member list", user_id, project_id
            )
        return member


def _build_slack_blocks(plan: dict) -> list:
    """Helper to build Block Kit blocks from the agent's action plan."""
    blocks = [
        {
            "type": SLACK_BLOCK_TYPE_HEADER,
            "text": {
                "type": SLACK_BLOCK_TEXT_PLAIN,
                "text": "🚀  Meeting Intelligence: Action Plan Ready",
            },
        },
        {
            "type": SLACK_BLOCK_TYPE_SECTION,
            "text": {
                "type": SLACK_BLOCK_TEXT_MRKDWN,
                "text": f"*Summary Reference*: {plan.get('meeting_summary_ref', 'N/A')}",
            },
        },
    ]

    new_tasks = plan.get("new_tasks", [])
    if new_tasks:
        text_part = "*Created New Tasks*:\n" + "\n".join(
            [f"• *{t['title']}* ({t['type']})" for t in new_tasks]
        )
        blocks.append(
            {
                "type": SLACK_BLOCK_TYPE_SECTION,
                "text": {"type": SLACK_BLOCK_TEXT_MRKDWN, "text": text_part},
            }
        )

    updated = plan.get("updated_tasks", [])
    if updated:
        text_part = "*Updated Backlog Items*:\n" + "\n".join(
            [f"• *{t['task_title']}*" for t in updated]
        )
        blocks.append(
            {
                "type": SLACK_BLOCK_TYPE_SECTION,
                "text": {"type": SLACK_BLOCK_TEXT_MRKDWN, "text": text_part},
            }
        )

    assignments = plan.get("assignments", [])
    if assignments:
        text_part = "*Assignments*:\n" + "\n".join(
            [
                f"• {a['assignee_name']} → Task ID: `{a['task_id'][:8]}`"
                for a in assignments
            ]
        )
        blocks.append(
            {
                "type": SLACK_BLOCK_TYPE_SECTION,
                "text": {"type": SLACK_BLOCK_TEXT_MRKDWN, "text": text_part},
            }
        )

    unresolved = plan.get("unresolved_items", [])
    if unresolved:
        text_part = "⚠️ *Unresolved Items (Flagged for Review)*:\n" + "\n".join(
            [f"• {u['description']}" for u in unresolved]
        )
        blocks.append(
            {
                "type": SLACK_BLOCK_TYPE_SECTION,
                "text": {"type": SLACK_BLOCK_TEXT_MRKDWN, "text": text_part},
            }
        )

    blocks.append({"type": SLACK_BLOCK_TYPE_DIVIDER})
    blocks.append(
        {
            "type": SLACK_BLOCK_TYPE_CONTEXT,
            "elements": [
                {
                    "type": SLACK_BLOCK_TEXT_MRKDWN,
                    "text": "View full details on the project dashboard.",
                }
            ],
        }
    )
    return blocks


async def post_task_mapping_notification(project_id: str, agent_response: str) -> bool:
    """
    Format and post the Task Mapper Agent output to the project's Slack channel.
    """
    try:
        with get_db_session() as db:
            slack_info = db.execute(
                text("""
                SELECT channel_id, bot_token 
                FROM project_slack_details 
                WHERE project_id = :pid
            """),
                {"pid": project_id},
            ).fetchone()

        if not slack_info or not slack_info[0]:
            logger.warning("No Slack channel configured for project %s", project_id)
            return False

        channel_id, bot_token = slack_info
        token = bot_token or settings.SLACK_BOT_TOKEN

        if not token:
            logger.warning("No Slack token available for project %s", project_id)
            return False

        try:
            json_str = agent_response.strip()
            if json_str.startswith("```json"):
                json_str = json_str.replace("```json", "").replace("```", "").strip()

            data = json.loads(json_str)
            plan = data.get("action_plan", {})
        except Exception:
            logger.error(
                "Failed to parse Agent JSON for Slack notification. Raw text: %s",
                agent_response,
            )
            plan = {
                "unresolved_items": [{"description": "Parsing error on agent response"}]
            }

        blocks = _build_slack_blocks(plan)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.SLACK_API_BASE_URL}/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"channel": channel_id, "blocks": blocks},
            )
            resp.raise_for_status()
            logger.info("Sent Task Mapper results to Slack channel %s", channel_id)
            return True

    except Exception as e:
        logger.exception("Slack notification delivery failed: %s", e)
        return False

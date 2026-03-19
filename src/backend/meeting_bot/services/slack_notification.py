import logging
import httpx
import json
from sqlalchemy import text
from src.backend.config import settings
from src.backend.meeting_bot.constants import (
    SLACK_BLOCK_TEXT_PLAIN,
    SLACK_BLOCK_TEXT_MRKDWN,
    SLACK_BLOCK_TYPE_HEADER,
    SLACK_BLOCK_TYPE_SECTION,
    SLACK_BLOCK_TYPE_DIVIDER,
    SLACK_BLOCK_TYPE_CONTEXT
)
from src.backend.meeting_bot.services.meeting.session import get_db_session

logger = logging.getLogger(__name__)

def _build_slack_blocks(plan: dict) -> list:
    """Helper to build Block Kit blocks from the agent's action plan."""
    blocks = [
        {
            "type": SLACK_BLOCK_TYPE_HEADER,
            "text": {"type": SLACK_BLOCK_TEXT_PLAIN, "text": "🚀  Meeting Intelligence: Action Plan Ready"}
        },
        {
            "type": SLACK_BLOCK_TYPE_SECTION,
            "text": {"type": SLACK_BLOCK_TEXT_MRKDWN, "text": f"*Summary Reference*: {plan.get('meeting_summary_ref', 'N/A')}"}
        }
    ]

    # New Tasks
    new_tasks = plan.get("new_tasks", [])
    if new_tasks:
        text_part = "*Created New Tasks*:\n" + "\n".join([f"• *{t['title']}* ({t['type']})" for t in new_tasks])
        blocks.append({"type": SLACK_BLOCK_TYPE_SECTION, "text": {"type": SLACK_BLOCK_TEXT_MRKDWN, "text": text_part}})

    # Updated Tasks
    updated = plan.get("updated_tasks", [])
    if updated:
        text_part = "*Updated Backlog Items*:\n" + "\n".join([f"• *{t['task_title']}*" for t in updated])
        blocks.append({"type": SLACK_BLOCK_TYPE_SECTION, "text": {"type": SLACK_BLOCK_TEXT_MRKDWN, "text": text_part}})

    # Assignments
    assignments = plan.get("assignments", [])
    if assignments:
        text_part = "*Assignments*:\n" + "\n".join([f"• {a['assignee_name']} → Task ID: `{a['task_id'][:8]}`" for a in assignments])
        blocks.append({"type": SLACK_BLOCK_TYPE_SECTION, "text": {"type": SLACK_BLOCK_TEXT_MRKDWN, "text": text_part}})

    # Unresolved
    unresolved = plan.get("unresolved_items", [])
    if unresolved:
        text_part = "⚠️ *Unresolved Items (Flagged for Review)*:\n" + "\n".join([f"• {u['description']}" for u in unresolved])
        blocks.append({"type": SLACK_BLOCK_TYPE_SECTION, "text": {"type": SLACK_BLOCK_TEXT_MRKDWN, "text": text_part}})

    blocks.append({"type": SLACK_BLOCK_TYPE_DIVIDER})
    blocks.append({
        "type": SLACK_BLOCK_TYPE_CONTEXT,
        "elements": [{"type": SLACK_BLOCK_TEXT_MRKDWN, "text": "View full details on the project dashboard."}]
    })
    return blocks

async def post_task_mapping_notification(project_id: str, agent_response: str) -> bool:
    """
    Format and post the Task Mapper Agent output to the project's Slack channel.
    """
    try:
        # 1. Fetch Slack integration details
        with get_db_session() as db:
            slack_info = db.execute(text("""
                SELECT channel_id, bot_token 
                FROM project_slack_details 
                WHERE project_id = :pid
            """), {"pid": project_id}).fetchone()

        if not slack_info or not slack_info[0]:
            logger.warning("No Slack channel configured for project %s", project_id)
            return False

        channel_id, bot_token = slack_info
        token = bot_token or settings.SLACK_BOT_TOKEN

        if not token:
            logger.warning("No Slack token available for project %s", project_id)
            return False

        # 2. Parse the agent response
        try:
            # The agent might return raw markdown JSON or just the JSON string
            json_str = agent_response.strip()
            if json_str.startswith("```json"):
                 json_str = json_str.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(json_str)
            plan = data.get("action_plan", {})
        except Exception:
            logger.error("Failed to parse Agent JSON for Slack notification. Raw text: %s", agent_response)
            plan = {"unresolved_items": [{"description": "Parsing error on agent response"}]}

        # 3. Format Slack Message (Block Kit)
        blocks = _build_slack_blocks(plan)

        # 4. Ship it to Slack
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.SLACK_API_BASE_URL}/chat.postMessage",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"channel": channel_id, "blocks": blocks}
            )
            resp.raise_for_status()
            logger.info("Sent Task Mapper results to Slack channel %s", channel_id)
            return True

    except Exception as e:
        logger.exception("Slack notification delivery failed: %s", e)
        return False

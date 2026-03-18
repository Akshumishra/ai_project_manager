"""
Slack Bot Service
Handles channel creation, bot join, and channel setup for projects.
"""
import re
import logging
import requests
from uuid import UUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _get_bot_token() -> str | None:
    from src.backend.config import settings
    return settings.SLACK_BOT_TOKEN


def _slack_api_post(endpoint: str, payload: dict) -> dict:
    """Generic POST to the Slack API."""
    token = _get_bot_token()
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured in settings.")

    response = requests.post(
        f"https://slack.com/api/{endpoint}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _slugify(name: str) -> str:
    """Convert a project name to a Slack-compatible channel name."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)     # allow only lowercase, digits, hyphens
    slug = re.sub(r"-{2,}", "-", slug)            # collapse repeated hyphens
    slug = slug.strip("-")                         # strip leading/trailing hyphens
    return slug[:80]                               # max 80 chars


def create_slack_channel(project_name: str) -> dict:
    """
    Create a Slack channel named after the project.
    If the name is taken, appends a random suffix and retries.
    Returns the full Slack API response dict.
    Raises on API error.
    """
    import uuid
    base_name = _slugify(project_name)
    
    for attempt in range(3):
        channel_name = base_name if attempt == 0 else f"{base_name}-{uuid.uuid4().hex[:4]}"
        
        # Max Slack channel name length is 80 chars
        if len(channel_name) > 80:
            channel_name = channel_name[:80].strip("-")
            
        result = _slack_api_post("conversations.create", {"name": channel_name})

        if result.get("ok"):
            logger.info("Created Slack channel '%s' (id=%s)", channel_name, result["channel"]["id"])
            return result
            
        error = result.get("error", "unknown_error")
        if error == "name_taken":
            logger.warning("Slack channel '%s' already exists. Retrying with suffix...", channel_name)
            continue
            
        raise RuntimeError(f"Slack conversations.create failed: {error}")
        
    raise RuntimeError(f"Could not create Slack channel for {project_name} after 3 attempts.")


def join_slack_channel(channel_id: str) -> dict:
    """
    Make the bot join a Slack channel by ID.
    Returns the full Slack API response dict.
    """
    result = _slack_api_post("conversations.join", {"channel": channel_id})

    if not result.get("ok"):
        error = result.get("error", "unknown_error")
        raise RuntimeError(f"Slack conversations.join failed: {error}")

    logger.info("Bot joined Slack channel id=%s", channel_id)
    return result


def setup_slack_channel_for_project(project_id: UUID, project_name: str) -> str | None:
    """
    Orchestrates: create channel → bot joins → returns channel_id.
    This is designed to run as a background task.
    Updates project.slack_channel_id in the database.

    Returns the channel_id on success, None on failure.
    """
    from src.backend.db.database import get_session_local
    from src.backend.model.project import Project

    db: Session = get_session_local()()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error("setup_slack_channel_for_project: project %s not found", project_id)
            return None

        # Skip if already set
        if project.slack_channel_id:
            logger.info("Project %s already has Slack channel %s", project_id, project.slack_channel_id)
            return project.slack_channel_id

        # Step 1: Create the channel
        try:
            create_result = create_slack_channel(project.name)
        except RuntimeError as e:
            logger.error("Failed to create Slack channel for project %s: %s", project_id, e)
            return None

        channel_id = create_result.get("channel", {}).get("id")
        if not channel_id:
            logger.error("No channel_id returned from Slack for project %s", project_id)
            return None

        # Step 2: Bot joins the channel
        try:
            join_slack_channel(channel_id)
        except RuntimeError as e:
            logger.warning("Bot failed to join channel %s: %s", channel_id, e)
            # Non-fatal — we still save the channel_id

        # Step 3: Save channel_id to project
        project.slack_channel_id = channel_id
        db.commit()
        logger.info("Saved Slack channel_id=%s to project %s", channel_id, project_id)
        return channel_id

    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error in setup_slack_channel_for_project: %s", e)
        return None
    finally:
        db.close()

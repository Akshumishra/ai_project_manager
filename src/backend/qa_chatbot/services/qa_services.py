import httpx
import uuid
from sqlalchemy import text
from typing import Optional, Dict, Any
from src.backend.config import settings
from src.backend.qa_chatbot.constants import SlackConstants, QAQueries
from src.backend.db.database import get_session_local
from src.backend.logger import get_logger

logger = get_logger("qa_services")

async def send_message(channel_id: str, text_content: str, thread_ts: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Sends a Slack message to a specific channel or thread."""
    url = SlackConstants.POST_MESSAGE_URL
    token = settings.SLACK_BOT_TOKEN
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    payload = {
        "channel": channel_id,
        "text": text_content
    }
    
    if thread_ts:
        payload["thread_ts"] = thread_ts
        
    logger.debug(f"Sending Slack message to channel {channel_id}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=SlackConstants.API_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                logger.error(f"Slack API error: {data.get('error')}")
                return None
            logger.debug("Slack message sent successfully")
            return data
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error {exc.response.status_code} while sending message: {exc.response.text}")
    except Exception as exc:
        logger.error(f"Unexpected error sending message to Slack: {exc}", exc_info=True)
        
    return None

def get_project_id_from_channel(channel_id: str) -> Optional[str]:
    """Find the project_id associated with a Slack channel."""
    logger.debug(f"Looking up project for channel: {channel_id}")
    factory = get_session_local()
    session = factory()
    try:
        row = session.execute(
            text(QAQueries.GET_PROJECT_ID_BY_CHANNEL), 
            {"channel_id": channel_id}
        ).fetchone()
        project_id = str(row[0]) if row else None
        if project_id:
            logger.debug(f"Found project_id: {project_id} for channel: {channel_id}")
        return project_id
    except Exception as e:
        logger.error(f"Error looking up project for channel {channel_id}: {e}", exc_info=True)
        return None
    finally:
        session.close()

def get_project_member_id(project_id: str, slack_user_id: str) -> Optional[str]:
    """Resolves the internal project_member_id for a Slack user in a given project."""
    logger.debug(f"Looking up member {slack_user_id} for project: {project_id}")
    factory = get_session_local()
    session = factory()
    try:
        # Set the project_id in the session for Row Level Security (RLS)
        session.execute(
            text("SET LOCAL app.project_id = :project_id"),
            {"project_id": project_id}
        )
        
        row = session.execute(
            text(QAQueries.GET_PROJECT_MEMBER_ID),
            {"project_id": project_id, "slack_id": slack_user_id}
        ).fetchone()
        member_id = str(row[0]) if row else None
        if member_id:
            logger.debug(f"Found member_id: {member_id} for user: {slack_user_id}")
        return member_id
    except Exception as e:
        logger.error(f"Error looking up member {slack_user_id}: {e}", exc_info=True)
        return None
    finally:
        session.close()

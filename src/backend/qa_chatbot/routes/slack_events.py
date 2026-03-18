import hmac
import hashlib
import time
import httpx
import json
from typing import Optional, Set, List, Dict, Any, Union
from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from src.backend.config import settings
from src.backend.qa_chatbot.constants import SlackConstants
from src.backend.qa_chatbot.services.qa_services import (
    send_message,
    get_project_id_from_channel,
    get_project_member_id,
)
from src.backend.qa_chatbot.qa_agent.agent import ProjectAwareAgent
from src.backend.logger import get_logger
from langchain_core.messages import HumanMessage, AIMessage

logger = get_logger("slack_events")
router = APIRouter(prefix="/api/slack", tags=["Slack Events"])

class SlackEvent(BaseModel):
    type: str
    user: Optional[str] = None
    text: Optional[str] = None
    ts: str
    channel: str
    thread_ts: Optional[str] = None
    subtype: Optional[str] = None

class SlackEventCallback(BaseModel):
    type: str
    token: str
    team_id: str
    api_app_id: str
    event: SlackEvent
    event_id: str
    event_time: int

class ChallengeResponse(BaseModel):
    challenge: str

class GenericResponse(BaseModel):
    status: str
    message_sent: bool = False
    detail: Optional[str] = None

processed_ts: Set[str] = set()

async def _get_validated_body(request: Request) -> Dict[str, Any]:
    """Handles signature verification and JSON parsing."""
    body_bytes = await request.body()

    try:
        await verify_slack_signature(request, body_bytes)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Verification error")

    try:
        return json.loads(body_bytes.decode())
    except Exception as e:
        logger.error(f"Failed to parse JSON body: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

def _handle_filtering(body: Dict[str, Any]) -> Union[Dict[str, Any], ChallengeResponse, GenericResponse]:
    """Handles challenges, deduplication, and message filtering."""

    if body.get("type") == "url_verification":
        return ChallengeResponse(challenge=body.get("challenge"))

    if body.get("type") != "event_callback":
        return GenericResponse(status="ignored", detail=f"Unsupported type: {body.get('type')}")

    event_data = body.get("event", {})
    ts = event_data.get("ts")

    if ts in processed_ts:
        return GenericResponse(status="duplicate", detail="Event already processed")
    
    processed_ts.add(ts)
    if len(processed_ts) > SlackConstants.MAX_TS_HISTORY:
        processed_ts.clear()

    if event_data.get("type") != "message":
        return GenericResponse(status="ignored", detail="Not a message event")

    slack_user_id = event_data.get("user")
    user_text = event_data.get("text", "")

    if not slack_user_id or slack_user_id == settings.BOT_USER_ID or event_data.get("subtype") == "bot_message":
        return GenericResponse(status="ignored", detail="Message from bot")

    mention_str = f"<@{settings.BOT_USER_ID}>"
    if mention_str not in user_text:
        return GenericResponse(status="ignored", detail="Bot not mentioned")

    return event_data

async def _orchestrate_agent(event_data: Dict[str, Any]) -> GenericResponse:
    """Handles context resolution and agent execution."""
    ts = event_data.get("ts")
    slack_user_id = event_data.get("user")
    user_text = event_data.get("text", "")
    channel_id = event_data.get("channel")
    thread_ts = event_data.get("thread_ts", ts)
    mention_str = f"<@{settings.BOT_USER_ID}>"

    try:
        question = user_text.replace(mention_str, "").strip()

        project_id = get_project_id_from_channel(channel_id)
        if not project_id:
            logger.warning(f"Project not found for channel {channel_id}")
            await send_message(channel_id, "Sorry, I couldn't find a project linked to this channel.", thread_ts=thread_ts)
            return GenericResponse(status="error", detail="No project found")

        member_id = get_project_member_id(project_id, slack_user_id)
        if not member_id:
            logger.warning(f"User {slack_user_id} not in project {project_id}")
            await send_message(channel_id, "Sorry, you don't appear to be a member of the project assigned to this channel.", thread_ts=thread_ts)
            return GenericResponse(status="error", detail="User not project member")

        history = await get_thread_history(channel_id, thread_ts)
        history.append(HumanMessage(content=question))
        
        agent = ProjectAwareAgent(project_id, slack_user_id, member_id)
        answer = agent.run(history)
        
        await send_message(channel_id, answer, thread_ts=thread_ts)
        return GenericResponse(status="success", message_sent=True)

    except Exception as e:
        logger.error(f"Error processing Slack event: {e}", exc_info=True)
        await send_message(channel_id, "I encountered an error while processing your request. Please try again later.", thread_ts=thread_ts)
        return GenericResponse(status="error", detail=str(e))


async def get_thread_history(channel_id: str, thread_ts: str) -> List[Any]:
    """Fetches thread conversation history from Slack."""
    url = SlackConstants.CONVERSATIONS_REPLIES_URL
    headers = {"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"}
    params  = {"channel": channel_id, "ts": thread_ts}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=SlackConstants.API_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("ok"):
                logger.error(f"Slack history API error: {data.get('error')}")
                return []

            messages = data.get("messages", [])
            history = []
            for msg in messages:
                text = msg.get("text", "")
                if not text:
                    continue
                
                if msg.get("bot_id") or msg.get("user") == settings.BOT_USER_ID:
                    history.append(AIMessage(content=text))
                else:
                    clean_text = text.replace(f"<@{settings.BOT_USER_ID}>", "").strip()
                    if clean_text:
                        history.append(HumanMessage(content=clean_text))
            
            return history
    except Exception as exc:
        logger.error(f"Failed to fetch thread history: {exc}")
        return []

async def verify_slack_signature(request: Request, body_bytes: bytes):
    """Verifies that the request came from Slack."""
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    
    if not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Slack headers")

    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Timestamp expired")

    signing_secret = settings.SLACK_SIGNING_SECRET
    if not signing_secret:
        logger.warning("SLACK_SIGNING_SECRET not set, bypassing verification")
        return

    sig_basestring = f"v0:{timestamp}:".encode() + body_bytes
    my_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(my_signature, signature):
        logger.error("Slack signature mismatch")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

@router.post("/events", response_model=Union[ChallengeResponse, GenericResponse, Dict[str, Any]])
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """Main entry point for Slack Event Subscriptions."""
    
    retry_num = request.headers.get("X-Slack-Retry-Num")
    if retry_num:
        logger.warning(f"Slack retry detected: {retry_num}. Reason: {request.headers.get('X-Slack-Retry-Reason')}")

    body = await _get_validated_body(request)

    result = _handle_filtering(body)
    
    if isinstance(result, (ChallengeResponse, GenericResponse)):
        return result

    background_tasks.add_task(_orchestrate_agent, result)
    
    return GenericResponse(status="accepted", detail="Processing in background")

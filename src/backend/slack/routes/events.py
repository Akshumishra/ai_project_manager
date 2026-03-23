import hmac
import hashlib
import time
import json
import logging
from typing import Optional, Set, Dict, Any, Union
from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from src.backend.config import settings
from src.backend.qa_chatbot.constants import SlackConstants
from src.backend.logger import get_logger

logger = get_logger("slack_events")
router = APIRouter(prefix="/api/slack", tags=["Slack Events"])

class ChallengeResponse(BaseModel):
    challenge: str

class GenericResponse(BaseModel):
    status: str
    message_sent: bool = False
    detail: Optional[str] = None

processed_ts: Set[str] = set()

async def verify_slack_signature(request: Request, body_bytes: bytes):
    """Verifies that the request came from Slack."""
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    
    if not timestamp or not signature:
        logger.error(f"Missing Slack headers: timestamp={timestamp}, signature={signature}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Slack headers")

    if abs(time.time() - int(timestamp)) > 60 * 5:
        logger.error(f"Timestamp expired: current={time.time()}, received={timestamp}")
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
        logger.error(f"Slack signature mismatch. Calculated: {my_signature}, Received: {signature}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

async def _get_validated_body(request: Request) -> Dict[str, Any]:
    """Handles signature verification and JSON parsing."""
    body_bytes = await request.body()
    await verify_slack_signature(request, body_bytes)
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
    is_mention = mention_str in user_text
    is_thread_reply = event_data.get("thread_ts") is not None
    
    if is_mention:
        event_data["dispatch_type"] = "qa"
        return event_data
        
    if is_thread_reply:
        event_data["dispatch_type"] = "standup"
        return event_data

    return GenericResponse(status="ignored", detail="Neither a mention nor a standup thread reply")

async def _orchestrate_dispatch(event_data: Dict[str, Any]):
    """Dispatches the event to the appropriate handler."""
    dispatch_type = event_data.get("dispatch_type")
    ts = event_data.get("ts")
    slack_user_id = event_data.get("user")
    user_text = event_data.get("text", "")
    channel_id = event_data.get("channel")
    thread_ts = event_data.get("thread_ts", ts)

    logger.info(f"Orchestrating dispatch for type: {dispatch_type}, channel: {channel_id}, thread_ts: {thread_ts}")

    if dispatch_type == "standup":
        from src.backend.standups.services.reply_handler import handle_standup_reply
        await handle_standup_reply(
                channel_id=channel_id,
                thread_ts=thread_ts,
                slack_user_id=slack_user_id,
                user_text=user_text,
                ts=ts
            )
    elif dispatch_type == "qa":
        from src.backend.qa_chatbot.services.mention_handler import handle_qa_mention
        await handle_qa_mention(channel_id, thread_ts, slack_user_id, user_text)

@router.post("/events", response_model=Union[ChallengeResponse, GenericResponse, Dict[str, Any]])
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """Main entry point for Slack Event Subscriptions."""
    body_bytes = await request.body()
    decoded_body = body_bytes.decode()
    
    with open("/tmp/slack_requests.log", "a") as f:
        f.write(f"[{time.ctime()}] RAW (processed_ts size: {len(processed_ts)}): {decoded_body[:1000]}\n")
        
    logger.info(f"Incoming Slack request: {decoded_body[:500]}...")
    
    await verify_slack_signature(request, body_bytes)
    try:
        body = json.loads(body_bytes.decode())
    except Exception as e:
        logger.error(f"Failed to parse JSON body: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    result = _handle_filtering(body)
    
    if isinstance(result, (ChallengeResponse, GenericResponse)):
        logger.info(f"Event filtered/handled early: {result}")
        return result

    background_tasks.add_task(_orchestrate_dispatch, result)
    logger.info(f"Event accepted and queued for background processing: dispatch_type={result.get('dispatch_type')}")
    return GenericResponse(status="accepted", detail="Processing in background")

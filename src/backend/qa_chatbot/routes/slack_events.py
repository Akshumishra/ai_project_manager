import os
import hmac
import hashlib
import time
import requests
import httpx
import traceback
from fastapi import APIRouter, Request, HTTPException
from langchain_core.messages import HumanMessage, AIMessage
from src.backend.config import Config
from src.backend.constants import SlackConstants
from src.backend.qa_chatbot.services.send_slack_message import send_message
from src.backend.qa_chatbot.services.context_resolver import (
    get_project_id_from_channel,
    get_project_member_id,
)
from src.backend.qa_chatbot.qa_agent.agent import ProjectAwareAgent
from src.backend.logger import get_logger

logger = get_logger("slack_events")

router = APIRouter()

logger.info(f"BOT_USER_ID={Config.BOT_USER_ID}")
logger.info(f"SLACK_BOT_TOKEN set={bool(Config.SLACK_BOT_TOKEN)}")

processed_ts: set = set()

async def get_thread_history(channel_id: str, thread_ts: str) -> list:
    url = SlackConstants.CONVERSATIONS_REPLIES_URL
    headers = {"Authorization": f"Bearer {Config.SLACK_BOT_TOKEN}"}
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
    except Exception as exc:
        logger.error(f"HTTP error fetching thread history: {exc}", exc_info=True)
        return []

    if not data.get("ok"):
        logger.error(f"Slack API error fetching thread history: {data.get('error')}")
        return []

    messages = data.get("messages", [])
    history: list = []

    for msg in messages:
        text     = msg.get("text", "")
        bot_id   = msg.get("bot_id")       
        user_id  = msg.get("user", "")

        if not text:
            continue

        if bot_id or user_id == Config.BOT_USER_ID:
            history.append(AIMessage(content=text))
        else:
            clean_text = text.replace(f"<@{Config.BOT_USER_ID}>", "").strip()
            if clean_text:
                history.append(HumanMessage(content=clean_text))

    logger.debug(f"Loaded {len(history)} messages from thread history")
    return history


@router.post("/slack/events")
async def slack_events(request: Request):
    # 1. Verify Slack Signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    
    if not timestamp or not signature:
        logger.error("Missing Slack verification headers")
        raise HTTPException(status_code=401, detail="Authentication failed")

    # Prevent replay attacks: reject if older than 5 minutes
    if abs(time.time() - int(timestamp)) > 60 * 5:
        logger.error("Slack request timestamp expired")
        raise HTTPException(status_code=401, detail="Authentication failed")

    body_bytes = await request.body()
    signing_secret = Config.SLACK_SIGNING_SECRET
    
    if not signing_secret:
        # Fallback for development if secret not set yet
        logger.warning("SLACK_SIGNING_SECRET not set, bypassing verification")
    else:
        sig_basestring = f"v0:{timestamp}:".encode() + body_bytes
        my_signature = "v0=" + hmac.new(
            signing_secret.encode(),
            sig_basestring,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(my_signature, signature):
            logger.error("Slack signature mismatch")
            raise HTTPException(status_code=401, detail="Authentication failed")

    # 2. Process Request
    try:
        import json
        body = json.loads(body_bytes.decode())
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    logger.debug("Received incoming verified request to /slack/events")
    logger.debug(f"Request type: {body.get('type')}")

    if body.get("type") == "url_verification":
        logger.info("URL verification challenge received")
        return {"challenge": body["challenge"]}

    if body.get("type") != "event_callback":
        logger.debug(f"Ignoring non-event_callback request: {body.get('type')}")
        return {"status": "ignored"}

    event      = body.get("event", {})
    event_type = event.get("type")
    ts         = event.get("ts")
    thread_ts  = event.get("thread_ts", ts)

    logger.debug(f"Event type: {event_type}, ts: {ts}, thread_ts: {thread_ts}")

    if ts in processed_ts:
        logger.debug(f"Ignoring duplicate event ts: {ts}")
        return {"status": "duplicate ignored"}
    processed_ts.add(ts)
    if len(processed_ts) > SlackConstants.MAX_TS_HISTORY:
        processed_ts.clear()

    if event_type != "message":
        logger.debug(f"Ignoring event type '{event_type}' (not a message)")
        return {"status": "ignored"}

    slack_user_id = event.get("user")
    user_message  = event.get("text", "")
    channel_id    = event.get("channel")

    if slack_user_id == Config.BOT_USER_ID or event.get("subtype") == "bot_message":
        logger.debug("Ignoring message from bot itself")
        return {"status": "ignored bot message"}

    mention_str = f"<@{Config.BOT_USER_ID}>"
    if mention_str not in user_message:
        logger.debug("Ignoring message: bot not mentioned")
        return {"status": "ignored"}

    question = user_message.replace(mention_str, "").strip()
    logger.debug(f"Received question: '{question}' from user {slack_user_id} in channel {channel_id}")

    # DEBUG: Write to a file since terminal output is hard to capture
    with open("/tmp/slack_debug.log", "a") as f:
        f.write(f"USER: {slack_user_id}, CHANNEL: {channel_id}, QUESTION: {question}\n")

    logger.debug(f"Looking up project for channel_id={channel_id}")
    project_id = get_project_id_from_channel(channel_id)
    if not project_id:
        logger.error(f"No project mapped to channel {channel_id}")
        await send_message(
            channel_id,
            "Sorry, I couldn't find a project linked to this channel.",
            thread_ts=thread_ts,
        )
        return {"status": "no project for channel"}

    logger.debug(f"Project ID resolved: {project_id}")
    logger.debug(f"Looking up member for slack_user_id={slack_user_id}")
    project_member_id = get_project_member_id(project_id, slack_user_id)
    if not project_member_id:
        logger.warning(f"User {slack_user_id} is not a member of project {project_id}")
        await send_message(
            channel_id,
            "Sorry, you don't appear to be a member of the project linked to this channel.",
            thread_ts=thread_ts,
        )
        return {"status": "user not project member"}

    logger.debug(f"Project member ID resolved: {project_member_id}")

    history = await get_thread_history(channel_id, thread_ts)
    history.append(HumanMessage(content=question))
    logger.debug(f"Total history messages including new question: {len(history)}")

    try:
        logger.debug("Initializing ProjectAwareAgent...")
        agent  = ProjectAwareAgent(project_id, slack_user_id, project_member_id)
        logger.info("Running agent reasoning...")
        answer = agent.run(history)
        logger.debug(f"Agent response: {answer}")
        logger.info("Agent response generated successfully")
        await send_message(channel_id, answer, thread_ts=thread_ts)
        return {"status": "ok", "message_sent": True}

    except Exception as exc:
        logger.error(f"Agent processing error: {exc}", exc_info=True)
        await send_message(
            channel_id,
            "Sorry, I ran into an error while processing your request.",
            thread_ts=thread_ts,
        )
        return {"status": "error", "message_sent": False}


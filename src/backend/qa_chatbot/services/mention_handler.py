from __future__ import annotations
import logging
import httpx
from typing import List, Any
from langchain_core.messages import HumanMessage, AIMessage

from src.backend.config import settings
from src.backend.qa_chatbot.constants import SlackConstants
from src.backend.qa_chatbot.services.qa_services import (
    send_message,
    get_project_id_from_channel,
    get_project_member_id,
)
from src.backend.qa_chatbot.qa_agent.agent import ProjectAwareAgent

logger = logging.getLogger(__name__)

async def handle_qa_mention(
    channel_id: str,
    thread_ts: str,
    slack_user_id: str,
    user_text: str
):
    """
    Handles a direct mention of the bot, orchestrating the QA Agent.
    """
    mention_str = f"<@{settings.BOT_USER_ID}>"
    question = user_text.replace(mention_str, "").strip()

    # 1. Context Resolution
    try:
        project_id = get_project_id_from_channel(channel_id)
        if not project_id:
            logger.warning(f"Project not found for channel {channel_id}")
            await send_message(channel_id, "⚠️ *Error*: I couldn't find a project linked to this channel. Please contact your administrator.", thread_ts=thread_ts)
            return

        member_id = get_project_member_id(project_id, slack_user_id)
        if not member_id:
            logger.warning(f"User {slack_user_id} not in project {project_id}")
            await send_message(channel_id, "⚠️ *Access Denied*: You don't appear to be a member of the project assigned to this channel.", thread_ts=thread_ts)
            return
    except Exception as e:
        logger.error(f"Context resolution failed: {e}")
        await send_message(channel_id, "⚠️ *Error*: I encountered a database problem while looking up your project details.", thread_ts=thread_ts)
        return

    # 2. Agent Execution
    try:
        history = await get_thread_history(channel_id, thread_ts)
        history.append(HumanMessage(content=question))
        
        agent = ProjectAwareAgent(project_id, slack_user_id, member_id)
        answer = await agent.arun(history)
        
        await send_message(channel_id, answer, thread_ts=thread_ts)
    except Exception as e:
        logger.error(f"Agent execution failed for user {slack_user_id}: {e}", exc_info=True)
        error_msg = "Sorry, I encountered an internal error while thinking about your question. Please try again in a moment."
        if "rate limit" in str(e).lower():
            error_msg = "I'm receiving too many requests right now. Please wait a minute before asking again."
        await send_message(channel_id, f"❌ {error_msg}", thread_ts=thread_ts)


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

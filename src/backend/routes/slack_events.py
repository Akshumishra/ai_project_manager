import logging
import uuid
from fastapi import APIRouter, Request, BackgroundTasks
from src.backend.services.standup_manager import StandupManager
from src.backend.db.database_standup import SessionStandup
from src.backend.model.standup import Standup

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack Events API webhooks.
    """
    data = await request.json()
    
    # URL Verification (for Slack setup)
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}

    event = data.get("event", {})
    
    # We are interested in message events that are replies in a thread
    if event.get("type") == "message" and event.get("thread_ts"):
        thread_ts = event.get("thread_ts")
        channel_id = event.get("channel")
        
        # Check if this thread_ts corresponds to an active standup
        db = SessionStandup()
        try:
            standup = db.query(Standup).filter(
                Standup.message_ts == thread_ts,
                Standup.slack_channel_id == channel_id
            ).first()
            
            if standup:
                logger.info(f"Detected reply in standup thread: {thread_ts}")
                # Process reply in background to keep Slack happy (3s timeout)
                background_tasks.add_task(process_reply, str(standup.id))
                
        finally:
            db.close()

    return {"status": "ok"}

def process_reply(standup_id: str):
    """Background task to process standup replies."""
    db = SessionStandup()
    try:
        manager = StandupManager(db)
        manager.process_new_replies(standup_id)
    except Exception as e:
        logger.error(f"Error processing background standup reply: {e}")
    finally:
        db.close()

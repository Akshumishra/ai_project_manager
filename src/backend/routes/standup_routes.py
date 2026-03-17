import logging
from fastapi import APIRouter, HTTPException
from src.backend.services.standup_manager import StandupManager
from src.backend.db.database_standup import SessionStandup

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/standup/trigger/{project_id}/{channel_id}")
async def trigger_standup(project_id: str, channel_id: str):
    """
    Manually triggers a standup for a project.
    """
    db = SessionStandup()
    try:
        manager = StandupManager(db)
        ts = manager.initiate_standup(project_id, channel_id)
        if not ts:
            raise HTTPException(status_code=500, detail="Failed to initiate standup")
        return {"status": "initiated", "message_ts": ts}
    except Exception as e:
        logger.error(f"Error triggering standup: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/standup/trigger-all")
async def trigger_all_standups():
    """
    Triggers standups for all configured projects.
    """
    db = SessionStandup()
    try:
        manager = StandupManager(db)
        results = manager.initiate_all_standups()
        return {"status": "batch_initiated", "results": results}
    except Exception as e:
        logger.error(f"Error triggering all standups: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/standup/process/{standup_id}")
async def process_standup_replies(standup_id: str):
    """
    Manually triggers processing of new replies in a standup thread.
    """
    db = SessionStandup()
    try:
        manager = StandupManager(db)
        manager.process_new_replies(standup_id)
        return {"status": "processing_triggered"}
    except Exception as e:
        logger.error(f"Error processing standup replies: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/standup/finalize/{standup_id}")
async def finalize_standup(standup_id: str):
    """
    Manually finalizes a standup and posts the summary.
    """
    db = SessionStandup()
    try:
        manager = StandupManager(db)
        manager.finalize_standup(standup_id)
        return {
            "status": "finalized",
            "message": "Standup summary posted successfully to Slack"
        }
    except ValueError as e:
        logger.error(f"Validation error finalizing standup {standup_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error finalizing standup {standup_id}: {e}", exc_info=True)
        error_detail = str(e)
        # Provide more helpful error messages
        if "SLACK_BOT_TOKEN" in error_detail:
            error_detail = "SLACK_BOT_TOKEN is not configured. Please set it in your environment variables."
        elif "Slack API error" in error_detail:
            error_detail = f"Slack API error: {error_detail}. Check your bot token and permissions."
        elif "Channel ID" in error_detail:
            error_detail = "Channel ID is missing. The standup may not have been properly initiated."
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        db.close()

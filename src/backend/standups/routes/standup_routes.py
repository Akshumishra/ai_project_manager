import logging
import uuid
from fastapi import APIRouter, HTTPException
from src.backend.standups.services.standup_manager import StandupManager
from src.backend.db.database_standup import SessionStandup

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/standup", tags=["Standup API"])

@router.post("/trigger/{project_id}/{channel_id}")
async def trigger_standup(project_id: str, channel_id: str):
    """
    Manually triggers a standup for a project.
    """
    db = SessionStandup()
    try:
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid project_id format: {project_id}")

        from src.backend.model.project import ProjectSlackDetail
        detail = db.query(ProjectSlackDetail).filter(ProjectSlackDetail.project_id == project_id).first()
        if not detail:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found or Slack not configured.")

        manager = StandupManager(db)
        ts = await manager.initiate_standup(project_id, channel_id)
        if not ts:
            raise HTTPException(status_code=500, detail="Failed to initiate standup—check logs for details.")
        return {"status": "initiated", "message_ts": ts}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering standup for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error triggering standup: {str(e)}")
    finally:
        db.close()

@router.post("/trigger-all")
async def trigger_all_standups():
    """
    Triggers standups for all configured projects.
    """
    db = SessionStandup()
    try:
        manager = StandupManager(db)
        results = await manager.initiate_all_standups()
        if not results:
            return {"status": "no_active_projects", "message": "No projects with Slack channels found."}
        return {"status": "batch_initiated", "results": results}
    except Exception as e:
        logger.error(f"Error triggering all standups: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error in batch initiation: {str(e)}")
    finally:
        db.close()

@router.post("/process/{standup_id}")
async def process_standup_replies(standup_id: str):
    """
    Manually triggers processing of new replies in a standup thread.
    """
    db = SessionStandup()
    try:
        try:
            uuid.UUID(standup_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid standup_id format: {standup_id}")

        from src.backend.model.standup import Standup
        standup = db.query(Standup).get(standup_id)
        if not standup:
            raise HTTPException(status_code=404, detail=f"Standup session {standup_id} not found.")

        manager = StandupManager(db)
        await manager.process_new_replies(standup_id)
        return {"status": "processing_triggered"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing standup {standup_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process replies: {str(e)}")
    finally:
        db.close()

@router.post("/finalize/{standup_id}")
async def finalize_standup(standup_id: str):
    """
    Manually finalizes a standup and posts the summary.
    """
    db = SessionStandup()
    try:
        try:
            uuid.UUID(standup_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid standup_id format: {standup_id}")

        from src.backend.model.standup import Standup
        standup = db.query(Standup).get(standup_id)
        if not standup:
            raise HTTPException(status_code=404, detail=f"Standup session {standup_id} not found.")
        
        if standup.summary:
            return {"status": "already_finalized", "message": "This standup has already been summarized."}

        manager = StandupManager(db)
        await manager.finalize_standup(standup_id)
        return {
            "status": "finalized",
            "message": "Standup summary posted successfully to Slack"
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error finalizing standup {standup_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error finalizing standup {standup_id}: {e}", exc_info=True)
        error_detail = str(e)
        # Specific Slack error mapping
        if "SLACK_BOT_TOKEN" in error_detail:
            error_detail = "SLACK_BOT_TOKEN is missing in environment."
        elif "not_in_channel" in error_detail:
            error_detail = "Bot is not in the required Slack channel."
        raise HTTPException(status_code=500, detail=f"Finalization failed: {error_detail}")
    finally:
        db.close()

@router.post("/finalize-all")
async def finalize_all_standups():
    """
    Finalizes all active standups from the last 24 hours.
    """
    db = SessionStandup()
    try:
        manager = StandupManager(db)
        results = await manager.finalize_all_active_standups()
        return {"status": "finalized", "standup_ids": results}
    except Exception as e:
        logger.error(f"Error in batch finalization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch finalization failed: {str(e)}")
    finally:
        db.close()

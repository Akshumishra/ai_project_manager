from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from meeting_bot.api.schemas import (
    JoinRequest,
    MultiJoinRequest,
    SessionResponse,
    StatusResponse,
)
from meeting_bot.bot.orchestrator import MultiSessionOrchestrator
from meeting_bot.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()

# Global orchestrator instance shared by routes
config = get_config()
orchestrator = MultiSessionOrchestrator(config)


@router.get("/", tags=["General"])
async def root():
    return {
        "message": "Google Meet Bot API is running.",
        "active_count": orchestrator.active_count,
    }


@router.post(
    "/sessions/join", response_model=SessionResponse, status_code=201, tags=["Sessions"]
)
async def join_meeting(request: JoinRequest):
    """Join a single meeting."""
    try:
        session_id = await orchestrator.start_session(
            meet_url=request.url,
            audio_device=request.audio_device,
            max_duration=request.max_duration,
        )
        return {"session_id": session_id, "url": request.url}
    except Exception as e:
        logger.exception("Failed to start session")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/sessions/join-multi",
    response_model=List[SessionResponse],
    status_code=201,
    tags=["Sessions"],
)
async def join_meetings(request: MultiJoinRequest):
    """Join multiple meetings concurrently."""
    responses = []
    for url in request.urls:
        try:
            session_id = await orchestrator.start_session(
                meet_url=url,
                audio_device=request.audio_device,
                max_duration=request.max_duration,
            )
            responses.append({"session_id": session_id, "url": url})
        except Exception as e:
            logger.error(f"Failed to start session for {url}: {e}")
    return responses


@router.get("/sessions", response_model=StatusResponse, tags=["Sessions"])
async def list_sessions():
    """List all active meeting sessions."""
    sessions = orchestrator.list_sessions()
    return {"active_sessions": sessions, "count": len(sessions)}


@router.delete("/sessions/{session_id}", tags=["Sessions"])
async def stop_session(session_id: str):
    """Stop an active meeting session."""
    success = await orchestrator.stop_session(session_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Session not found or already stopped."
        )
    return {"message": f"Session {session_id} stopping..."}


async def shutdown_orchestrator():
    """Helper to wait for all sessions to finish."""
    logger.info("Cleaning up all active sessions...")
    await orchestrator.wait_all()

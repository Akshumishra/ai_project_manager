from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from src.backend.meeting_bot.api.schemas import FirefliesWebhookPayload
from src.backend.meeting_bot.services.fireflies_client import FirefliesWebhookService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Webhooks"])


@router.post("/webhooks/fireflies/transcript", status_code=status.HTTP_200_OK)
async def fireflies_transcript_webhook(
    payload: FirefliesWebhookPayload,
) -> dict:
    """
    Webhook target for Fireflies.ai.
    """
    target_id = payload.transcript_id or payload.meeting_id
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing both transcriptId and meetingId.",
        )

    service = FirefliesWebhookService()

    try:
        data = await service.fetch_and_map_transcript(target_id)
        if data["status"] == "empty":
            return {"status": "ignored", "reason": "empty_transcript"}

        resolved_session_id = await service.ingest_transcript(
            payload.bot_session_id, data
        )

        logger.info(
            "Successfully ingested transcript for session %s", resolved_session_id
        )
        return {"status": "success", "message": "Transcript processed."}

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception:
        logger.exception("Unexpected error in transcript webhook")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcript processing failed.",
        )

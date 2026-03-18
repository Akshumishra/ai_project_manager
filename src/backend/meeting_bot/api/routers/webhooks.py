from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, status

from src.backend.meeting_bot.api.schemas import FirefliesWebhookPayload
from src.backend.services.fireflies_client import FirefliesClient
from src.backend.services.meeting import mark_meeting_ended, upsert_transcript

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Webhooks"])


@router.post("/webhooks/fireflies/transcript", status_code=status.HTTP_200_OK)
async def fireflies_transcript_webhook(
    payload: FirefliesWebhookPayload,
) -> dict:
    """
    Webhook target for Fireflies.ai when a transcript is completed.

    Flow:
    1. Fetch full transcript securely from Fireflies API.
    2. Map to internal schema and persist.
    3. Trigger AI analysis pipeline.
    """
    ffl_client = FirefliesClient()

    # ── 1. Fetch transcript payload securely ────────────────────────────────
    target_id = payload.transcript_id or payload.meeting_id
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing both transcriptId and meetingId in webhook payload.",
        )

    try:
        raw_data = await ffl_client.fetch_transcript(target_id)
    except Exception:
        logger.exception("Failed to fetch transcript from Fireflies for %s", target_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch transcript from upstream provider.",
        )

    sentences = raw_data.get("sentences", [])
    if not sentences:
        logger.warning(
            "Webhook received but no sentences found for transcript %s", target_id
        )
        return {"status": "ignored", "reason": "empty_transcript"}

    # ── 2. Map Fireflies schema to internal transcript schema ──────────────
    mapped_segments = []
    full_text_parts = []

    for s in sentences:
        text = s.get("text", "")
        speaker = s.get("speaker_name", "Unknown")
        full_text_parts.append(f"{speaker}: {text}")

        mapped_segments.append(
            {
                "sequence": s.get("index", 0),
                "start_ms": (
                    int(float(s.get("start_time", 0)) * 1000)
                    if s.get("start_time")
                    else 0
                ),
                "end_ms": (
                    int(float(s.get("end_time", 0)) * 1000)
                    if s.get("end_time")
                    else 0
                ),
                "speaker_label": speaker,
                "speaker_member_id": None,
                "text": text,
            }
        )

    raw_text_concat = "\n".join(full_text_parts)

    # ── 3. Upsert into DB ──────────────────────────────────────────────────
    meet_url = raw_data.get("meeting_link")

    try:
        resolved_bot_session_id = await asyncio.to_thread(
            upsert_transcript,
            bot_session_id=payload.bot_session_id,
            raw_text=raw_text_concat,
            segments=mapped_segments,
            provider="fireflies",
            meet_url=meet_url,
        )

        if resolved_bot_session_id:
            await asyncio.to_thread(mark_meeting_ended, resolved_bot_session_id)

    except Exception:
        logger.exception("Failed to persist Fireflies transcript to DB")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcript processing failed. Please contact support.",
        )

    logger.info(
        "Successfully ingested Fireflies transcript for session %s",
        resolved_bot_session_id or "unknown",
    )
    return {"status": "success", "message": "Transcript fetched and AI analysis triggered."}

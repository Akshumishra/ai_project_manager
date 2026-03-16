from __future__ import annotations

import logging
import threading
from uuid import UUID

from src.backend.model.meeting import (
    Meeting,
    MeetingStatus,
    MeetingTranscript,
    TranscriptStatus,
)
from src.backend.services.meeting.session import get_db_session, get_meeting_by_session

logger = logging.getLogger(__name__)


def create_transcript_record(bot_session_id: str) -> UUID | None:
    """Create a MeetingTranscript stub with status=PENDING."""
    with get_db_session() as db:
        meeting = get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning(
                "create_transcript_record: no row for bot_session=%s", bot_session_id
            )
            return None

        transcript = MeetingTranscript(
            meeting_id=meeting.id,
            status=TranscriptStatus.PENDING,
        )
        db.add(transcript)
        db.flush()
        transcript_id = transcript.id

    logger.info(
        "Transcript stub created: id=%s meeting_id=%s", transcript_id, meeting.id
    )
    return transcript_id


def upsert_transcript(
    bot_session_id: str | None = None,
    *,
    raw_text: str,
    segments: list[dict],
    language: str = "en",
    provider: str | None = None,
    meet_url: str | None = None,
) -> str | None:
    """
    Write (or overwrite) transcript content and flip status → COMPLETED.

    Resolution strategy:
    1. Look up by ``bot_session_id`` (direct match).
    2. Fall back to ``meet_url`` for webhook-sourced transcripts.

    After persisting, triggers the AI analysis pipeline in a background thread.
    """
    with get_db_session() as db:
        meeting = None
        if bot_session_id:
            meeting = get_meeting_by_session(db, bot_session_id)

        if meeting is None and meet_url:
            meeting = (
                db.query(Meeting)
                .filter(
                    Meeting.meet_url == meet_url,
                    Meeting.status != MeetingStatus.CANCELLED,
                )
                .order_by(Meeting.scheduled_at.desc())
                .first()
            )
            if meeting:
                bot_session_id = meeting.bot_session_id

        if meeting is None:
            logger.warning(
                "upsert_transcript: no row for bot_session=%s and meet_url=%s",
                bot_session_id,
                meet_url,
            )
            return None

        transcript = (
            db.query(MeetingTranscript)
            .filter(MeetingTranscript.meeting_id == meeting.id)
            .first()
        )
        if transcript is None:
            transcript = MeetingTranscript(meeting_id=meeting.id)
            db.add(transcript)

        transcript.status = TranscriptStatus.COMPLETED
        transcript.raw_text = raw_text
        transcript.segments = segments
        transcript.language = language
        transcript.provider = provider
        transcript.word_count = len(raw_text.split())

    logger.info("Transcript upserted for bot_session=%s", bot_session_id)

    # ── Trigger Automatic AI Analysis Pipeline ───────────────────────────────
    _trigger_ai_analysis(bot_session_id, raw_text)

    return bot_session_id


def _trigger_ai_analysis(bot_session_id: str | None, raw_text: str) -> None:
    """
    Spawn a background thread for AI transcript analysis.

    Errors are caught and logged to prevent silent failures in the
    fire-and-forget thread.
    """
    if not bot_session_id:
        return

    def _run_processor() -> None:
        try:
            from src.backend.services.ai.processor import process_meeting_transcript

            process_meeting_transcript(bot_session_id, raw_text)
        except Exception:
            logger.exception(
                "Background AI analysis thread failed for session %s", bot_session_id
            )

    thread = threading.Thread(
        target=_run_processor,
        daemon=True,
        name=f"AiProcessor-{bot_session_id}",
    )
    thread.start()
    logger.info(
        "Triggered AI analysis background thread for session %s", bot_session_id
    )

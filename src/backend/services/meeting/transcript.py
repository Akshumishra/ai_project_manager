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
    meeting_attendees: list[dict] | None = None,
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

        # ── Resolve Speaker Member IDs from Email Matching ──────────────────
        if meeting_attendees and meeting:
            # Build name->email map from Fireflies attendees
            attendee_email_map = {
                a.get("name"): a.get("email")
                for a in meeting_attendees
                if a.get("email")
            }

            # Map project member IDs by their associated user emails
            from src.backend.model.project import ProjectMember
            from src.backend.model.user import User

            member_emails = (
                db.query(ProjectMember.id, User.email)
                .join(User, ProjectMember.user_id == User.id)
                .filter(ProjectMember.project_id == meeting.project_id)
                .all()
            )
            email_to_member_id = {email: str(mid) for mid, email in member_emails}

            resolved_member_ids = set()
            for seg in segments:
                label = seg.get("speaker_label")
                email = attendee_email_map.get(label)
                if email and email in email_to_member_id:
                    member_id = email_to_member_id[email]
                    seg["speaker_member_id"] = member_id
                    resolved_member_ids.add(member_id)

            # ── Sync meeting_participants table ──────────────────────────────
            from src.backend.model.meeting import MeetingParticipant

            existing_member_ids = {
                str(p.project_member_id)
                for p in db.query(MeetingParticipant.project_member_id)
                .filter(MeetingParticipant.meeting_id == meeting.id)
                .all()
            }

            for member_id_str in resolved_member_ids:
                if member_id_str not in existing_member_ids:
                    db.add(
                        MeetingParticipant(
                            meeting_id=meeting.id,
                            project_member_id=UUID(member_id_str),
                        )
                    )
            db.flush()

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
            from src.backend.services.llm.meeting_analysis import process_meeting_transcript
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

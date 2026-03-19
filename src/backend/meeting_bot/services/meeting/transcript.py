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
from src.backend.meeting_bot.services.meeting.session import get_db_session, get_meeting_by_session
from src.backend.meeting_bot.constants import DEFAULT_TRANSCRIPT_LANGUAGE

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


def _sync_meeting_participants(db, meeting_id: UUID, project_id: UUID, attendees: list[dict], segments: list[dict]) -> None:
    """Helper to resolve attendee emails to project members, sync DB, and enrich segments."""
    from src.backend.model.project import ProjectMember
    from src.backend.model.user import User
    from src.backend.model.meeting import MeetingParticipant

    # 1. Fetch all project members and their emails for matching
    member_info = (
        db.query(ProjectMember.id, User.email)
        .join(User, ProjectMember.user_id == User.id)
        .filter(ProjectMember.project_id == project_id)
        .all()
    )
    email_to_member_id = {email.lower(): str(mid) for mid, email in member_info}

    # 2. Resolve Fireflies attendees to internal member IDs
    logger.info("Syncing %d attendees for meeting %s", len(attendees), meeting_id)
    attendee_name_to_id = {}
    resolved_member_ids = set()

    for a in attendees:
        name = a.get("name")
        email = (a.get("email") or "").lower()
        if email in email_to_member_id:
            member_id = email_to_member_id[email]
            resolved_member_ids.add(member_id)
            if name:
                attendee_name_to_id[name] = member_id
            logger.debug("Resolved attendee %s to member %s", email, member_id)

    # 3. Batch sync to meeting_participants table
    existing_participants = {
        str(p.project_member_id)
        for p in db.query(MeetingParticipant.project_member_id)
        .filter(MeetingParticipant.meeting_id == meeting_id)
        .all()
    }

    for member_id_str in resolved_member_ids:
        if member_id_str not in existing_participants:
            db.add(
                MeetingParticipant(
                    meeting_id=meeting_id,
                    project_member_id=UUID(member_id_str),
                )
            )
    
    # 4. Map speakers in segments for AI Agent context
    for seg in segments:
        label = seg.get("speaker_label")
        if label in attendee_name_to_id:
            seg["speaker_member_id"] = attendee_name_to_id[label]

    db.flush()
    logger.info("Successfully synced %d participants to DB", len(resolved_member_ids))

def upsert_transcript(
    bot_session_id: str | None = None,
    *,
    raw_text: str,
    segments: list[dict],
    language: str = DEFAULT_TRANSCRIPT_LANGUAGE,
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
        meeting = get_meeting_by_session(db, bot_session_id) if bot_session_id else None

        if not meeting and meet_url:
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

        # ── Resolve and Sync Participants ────────────────────────────────────
        if meeting:
            _sync_meeting_participants(
                db=db,
                meeting_id=meeting.id,
                project_id=meeting.project_id,
                attendees=meeting_attendees or [],
                segments=segments
            )

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
            from src.backend.meeting_bot.services.llm.meeting_analysis import process_meeting_transcript
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

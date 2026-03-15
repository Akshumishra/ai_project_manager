"""
src.backend.db.meeting_service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Repository layer for Module 4 — Intelligent Meeting Management.

All database write-paths for meeting data flow through this module so that
orchestrator.py and session_manager.py stay free of raw SQLAlchemy session
handling.  Read-paths (list, get) belong in the API route handlers.

Engine / session management is delegated entirely to
``src.backend.db.database`` — no second engine is created here.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator
from uuid import UUID

from sqlalchemy.orm import Session

from src.backend.db.database import get_session_local
from src.backend.model.meeting import (
    InviteSource,
    Meeting,
    MeetingActionItem,
    MeetingParticipant,
    MeetingStatus,
    MeetingSummary,
    MeetingTranscript,
    MeetingType,
    ParticipantRole,
    TranscriptStatus,
)

logger = logging.getLogger(__name__)


# ── Session context manager ────────────────────────────────────────────────────


@contextmanager
def _session() -> Generator[Session, None, None]:
    """Yield a transactional DB session; rolls back on error, always closes."""
    factory = get_session_local()
    db: Session = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Helper ─────────────────────────────────────────────────────────────────────


def _get_meeting_by_session(db: Session, bot_session_id: str) -> Meeting | None:
    """Fetch a Meeting by its bot_session_id within an open session."""
    return (
        db.query(Meeting)
        .filter(Meeting.bot_session_id == bot_session_id)
        .first()
    )


# ── Public API ─────────────────────────────────────────────────────────────────


def create_meeting(
    *,
    project_id: UUID,
    created_by: UUID,
    title: str,
    meet_url: str,
    bot_session_id: str,
    meeting_type: MeetingType = MeetingType.AD_HOC,
    task_id: UUID | None = None,
    agenda: str | None = None,
    scheduled_at: datetime | None = None,
) -> UUID:
    """
    Persist a new Meeting row as soon as the bot session is created.

    Returns the new ``meeting.id`` so downstream callers can reference it
    without an extra SELECT.
    """
    meeting = Meeting(
        project_id=project_id,
        created_by=created_by,
        title=title,
        meet_url=meet_url,
        bot_session_id=bot_session_id,
        meeting_type=meeting_type,
        status=MeetingStatus.SCHEDULED,
        task_id=task_id,
        agenda=agenda,
        scheduled_at=scheduled_at or datetime.now(timezone.utc),
    )
    with _session() as db:
        db.add(meeting)
        db.flush()  # Populate meeting.id before commit.
        meeting_id = meeting.id

    logger.info("Meeting created: id=%s bot_session=%s", meeting_id, bot_session_id)
    return meeting_id


def mark_meeting_started(bot_session_id: str) -> None:
    """
    Flip status → IN_PROGRESS and record the actual start timestamp.

    Called immediately after ``bot.join_meeting()`` succeeds.
    """
    with _session() as db:
        meeting = _get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("mark_meeting_started: no row for bot_session=%s", bot_session_id)
            return
        meeting.status = MeetingStatus.IN_PROGRESS
        meeting.started_at = datetime.now(timezone.utc)

    logger.info("Meeting started: bot_session=%s", bot_session_id)


def mark_meeting_ended(bot_session_id: str) -> None:
    """
    Flip status → COMPLETED and record the actual end timestamp.

    Called inside the ``finally`` block of the orchestrator's ``_run_session``
    after the bot has left the meeting.
    """
    with _session() as db:
        meeting = _get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("mark_meeting_ended: no row for bot_session=%s", bot_session_id)
            return
        meeting.status = MeetingStatus.COMPLETED
        meeting.ended_at = datetime.now(timezone.utc)

    logger.info("Meeting ended: bot_session=%s", bot_session_id)


def mark_meeting_cancelled(bot_session_id: str) -> None:
    """
    Flip status → CANCELLED.

    Called when a session is stopped via ``DELETE /sessions/{id}`` before the
    meeting naturally ends.
    """
    with _session() as db:
        meeting = _get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("mark_meeting_cancelled: no row for bot_session=%s", bot_session_id)
            return
        meeting.status = MeetingStatus.CANCELLED
        meeting.ended_at = datetime.now(timezone.utc)

    logger.info("Meeting cancelled: bot_session=%s", bot_session_id)


def create_transcript_record(bot_session_id: str) -> UUID | None:
    """
    Create a MeetingTranscript stub with status=PENDING.

    Called immediately after the meeting ends so the transcription pipeline
    has a row to update when results arrive.

    Returns the ``transcript.id``, or ``None`` if the parent meeting is not found.
    """
    with _session() as db:
        meeting = _get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("create_transcript_record: no row for bot_session=%s", bot_session_id)
            return None

        transcript = MeetingTranscript(
            meeting_id=meeting.id,
            status=TranscriptStatus.PENDING,
        )
        db.add(transcript)
        db.flush()
        transcript_id = transcript.id

    logger.info("Transcript stub created: id=%s meeting_id=%s", transcript_id, meeting.id)
    return transcript_id


def upsert_transcript(
    bot_session_id: str,
    *,
    raw_text: str,
    segments: list[dict],
    language: str = "en",
    provider: str | None = None,
) -> None:
    """
    Write (or overwrite) transcript content and flip status → COMPLETED.

    ``segments`` must follow the documented JSONB schema::

        [
          {
            "sequence": int,
            "start_ms": int,
            "end_ms": int,
            "speaker_label": str,
            "speaker_member_id": str | null,
            "text": str,
          },
          ...
        ]
    """
    with _session() as db:
        meeting = _get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("upsert_transcript: no row for bot_session=%s", bot_session_id)
            return

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


def save_summary(
    bot_session_id: str,
    *,
    summary_text: str,
    key_decisions: list[dict] | None = None,
    risks_and_blockers: list[dict] | None = None,
    ai_model: str | None = None,
    document_id: UUID | None = None,
) -> None:
    """
    Persist the AI-generated summary for a completed meeting.

    Idempotent: an existing summary row is overwritten rather than duplicated.
    """
    with _session() as db:
        meeting = _get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("save_summary: no row for bot_session=%s", bot_session_id)
            return

        summary = (
            db.query(MeetingSummary)
            .filter(MeetingSummary.meeting_id == meeting.id)
            .first()
        )
        if summary is None:
            summary = MeetingSummary(meeting_id=meeting.id)
            db.add(summary)

        summary.summary_text = summary_text
        summary.key_decisions = key_decisions
        summary.risks_and_blockers = risks_and_blockers
        summary.ai_model = ai_model
        summary.document_id = document_id
        summary.generated_at = datetime.now(timezone.utc)

    logger.info("Meeting summary saved for bot_session=%s", bot_session_id)


def add_action_items(bot_session_id: str, items: list[dict]) -> None:
    """
    Bulk-insert AI-extracted action items for a meeting.

    Each dict must have at least ``description``.  Optional keys:
    ``source_quote``, ``assigned_to_member_id`` (UUID str), ``due_date``
    (ISO-8601 str or datetime).

    Example::

        add_action_items("a3f8c12b", [
            {
                "description": "Write unit tests for auth module",
                "assigned_to_member_id": "550e8400-e29b-41d4-a716-446655440000",
                "source_quote": "Akshita, can you cover the tests by Friday?",
            }
        ])
    """
    with _session() as db:
        meeting = _get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("add_action_items: no row for bot_session=%s", bot_session_id)
            return

        for item in items:
            due_date = item.get("due_date")
            if isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date)

            assigned_id = item.get("assigned_to_member_id")
            db.add(
                MeetingActionItem(
                    meeting_id=meeting.id,
                    description=item["description"],
                    source_quote=item.get("source_quote"),
                    assigned_to_member_id=UUID(assigned_id) if assigned_id else None,
                    due_date=due_date,
                )
            )

    logger.info("Added %d action item(s) for bot_session=%s", len(items), bot_session_id)


def add_participants(bot_session_id: str, participants: list[dict]) -> None:
    """
    Bulk-insert participant records for a meeting.

    Each dict must have ``project_member_id``.  Optional keys:
    ``invite_source``, ``invite_reason``, ``role_in_meeting``.

    Existing (meeting, project_member) pairs are silently skipped — this call
    is idempotent.
    """
    with _session() as db:
        meeting = _get_meeting_by_session(db, bot_session_id)
        if meeting is None:
            logger.warning("add_participants: no row for bot_session=%s", bot_session_id)
            return

        existing_ids = {
            str(p.project_member_id)
            for p in db.query(MeetingParticipant)
            .filter(MeetingParticipant.meeting_id == meeting.id)
            .all()
        }

        for p in participants:
            member_id = str(p["project_member_id"])
            if member_id in existing_ids:
                continue

            db.add(
                MeetingParticipant(
                    meeting_id=meeting.id,
                    project_member_id=UUID(member_id),
                    invite_source=InviteSource(
                        p.get("invite_source", InviteSource.MANUALLY_ADDED)
                    ),
                    invite_reason=p.get("invite_reason"),
                    role_in_meeting=ParticipantRole(
                        p.get("role_in_meeting", ParticipantRole.ATTENDEE)
                    ),
                )
            )

    logger.info("Participants added for bot_session=%s", bot_session_id)

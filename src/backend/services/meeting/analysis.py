import logging
from datetime import datetime, timezone
from uuid import UUID

from src.backend.model.meeting import MeetingSummary, MeetingActionItem
from src.backend.services.meeting.session import get_db_session, get_meeting_by_session

logger = logging.getLogger(__name__)

def save_summary(
    bot_session_id: str,
    *,
    summary_text: str,
    key_decisions: list[dict] | None = None,
    risks_and_blockers: list[dict] | None = None,
    ai_model: str | None = None,
    document_id: UUID | None = None,
) -> None:
    """Persist the AI-generated summary for a completed meeting."""
    with get_db_session() as db:
        meeting = get_meeting_by_session(db, bot_session_id)
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
    """Bulk-insert AI-extracted action items for a meeting."""
    with get_db_session() as db:
        meeting = get_meeting_by_session(db, bot_session_id)
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

import logging
from uuid import UUID

from src.backend.model.meeting import MeetingParticipant, InviteSource, ParticipantRole
from src.backend.meeting_bot.services.meeting.session import get_db_session, get_meeting_by_session

logger = logging.getLogger(__name__)

def add_participants(bot_session_id: str, participants: list[dict]) -> None:
    """Bulk-insert participant records for a meeting."""
    with get_db_session() as db:
        meeting = get_meeting_by_session(db, bot_session_id)
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

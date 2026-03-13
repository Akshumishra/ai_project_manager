from sqlalchemy import text
from src.backend.db.database import SessionLocal
from src.backend.logger import get_logger

logger = get_logger("context_resolver")

def get_project_id_from_channel(channel_id: str) -> str | None:
    logger.debug(f"Looking up project for channel: {channel_id}")
    query = text("""
        SELECT project_id
        FROM project_slack_details
        WHERE channel_id = :channel_id
          AND deleted_at IS NULL
        LIMIT 1
    """)
    session = SessionLocal()
    try:
        row = session.execute(query, {"channel_id": channel_id}).fetchone()
        project_id = str(row[0]) if row else None
        if project_id:
            logger.debug(f"Found project_id: {project_id} for channel: {channel_id}")
        else:
            res = session.execute(text("SELECT current_setting('app.project_id', true)")).fetchone()
            logger.warning(f"No project found for channel: {channel_id}. Session app.project_id: {res[0]!r}")
        return project_id
    except Exception as e:
        logger.error(f"Error looking up project for channel {channel_id}: {e}", exc_info=True)
        return None
    finally:
        session.close()


def get_project_member_id(project_id: str, slack_user_id: str) -> str | None:
    logger.debug(f"Looking up member {slack_user_id} for project: {project_id}")
    query = text("""
        SELECT id
        FROM project_members
        WHERE project_id = :project_id
          AND slack_id   = :slack_id
          AND deleted_at IS NULL
        LIMIT 1
    """)
    session = SessionLocal()
    try:
        # Set the project_id in the session for Row Level Security (RLS)
        session.execute(
            text("SET LOCAL app.project_id = :project_id"),
            {"project_id": project_id}
        )
        
        row = session.execute(
            query,
            {"project_id": project_id, "slack_id": slack_user_id}
        ).fetchone()
        member_id = str(row[0]) if row else None
        if member_id:
            logger.debug(f"Found member_id: {member_id} for user: {slack_user_id}")
        else:
            logger.warning(f"User {slack_user_id} is not a member of project {project_id}")
        return member_id
    except Exception as e:
        logger.error(f"Error looking up member {slack_user_id}: {e}", exc_info=True)
        return None
    finally:
        session.close()

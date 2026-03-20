import logging
from typing import List, Dict, Type
from uuid import UUID
from sqlalchemy.orm import Session
from src.backend.model.project import ProjectMember

logger = logging.getLogger(__name__)


def get_agent_chat_history(
    db: Session,
    chat_model: Type,
    project_id: UUID
) -> List[Dict[str, str]]:
    """
    Fetch all chat messages for a given project, ordered by creation time.
    Works with any chat model (RequirementChat, TechDocChat, TaskAssignerChat, etc.).

    Returns a list of {"role": ..., "content": ...} dicts.
    """
    try:
        chats = (
            db.query(chat_model)
            .filter(chat_model.project_id == project_id)
            .order_by(chat_model.created_at)
            .all()
        )
        return [{"role": c.role, "content": c.content} for c in chats]
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to fetch chat history for project {project_id}: {e}")
        return []


def save_agent_chat_message(
    db: Session,
    chat_model: Type,
    project_id: UUID,
    role: str,
    content: str,
    user_id: UUID = None,
) -> None:
    """
    Persist a single chat message for any agent.
    Resolves `user_id` to a `project_member_id` if provided.

    Args:
        db: The current database session.
        chat_model: The SQLAlchemy model class for the chat (e.g. TechDocChat).
        project_id: UUID of the project this message belongs to.
        role: "user" or "assistant".
        content: The message text.
        user_id: Optional UUID of the user, used to resolve project membership.
    """
    try:
        project_member_id = None
        if user_id:
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            ).first()
            if member:
                project_member_id = member.id

        db.add(chat_model(
            project_id=project_id,
            role=role,
            content=content,
            project_member_id=project_member_id,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save chat message for project {project_id}: {e}")

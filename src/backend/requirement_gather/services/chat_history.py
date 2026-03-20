import logging
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.model.requirement_chat import RequirementChat
from src.backend.requirement_gather.requirement_agent.prompt import USER_PROMPT
from src.backend.utils.agent_chat_utils import get_agent_chat_history, save_agent_chat_message
from src.backend.utils.get_project_details import get_project_detail
from src.backend.model.project import ProjectMember

logger = logging.getLogger(__name__)


def get_chat_history(db: Session, project_id: UUID) -> list:
    return get_agent_chat_history(db, RequirementChat, project_id)


def save_chat_message(db: Session, project_id: UUID, role: str, content: str, user_id: UUID = None):
    save_agent_chat_message(db, RequirementChat, project_id, role, content, user_id)


def build_initial_user_prompt(db: Session, project_id: UUID, user_id: UUID = None) -> str:
    """
    Build the system-level context message placed at the start of every conversation.
    Includes the project title, description, and user's technical background (if any).
    """
    try:
        project = get_project_detail(db, project_id)
        background = None
        if user_id:
            background = db.query(ProjectMember.background).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            ).scalar()

        return USER_PROMPT.format(
            project_title=project["name"].strip(),
            project_description=project["description"].strip(),
            technical_background=background or "",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error building initial prompt for project {project_id}: {e}")
        return "Please describe your project requirements."

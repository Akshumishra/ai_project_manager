from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.model.requirement_chat import RequirementChat
from src.backend.model.project import ProjectMember
from src.backend.requirement_gather.requirement_agent.prompt import USER_PROMPT
from src.backend.utils import get_project_detail


def get_chat_history(db: Session, project_id: UUID) -> list:
    chats = (
        db.query(RequirementChat)
        .filter(RequirementChat.project_id == project_id)
        .order_by(RequirementChat.created_at)
        .all()
    )
    history = [
        {
            "role": chat.role,
            "content": chat.content
        }
        for chat in chats
    ]
    return history

def initialize_chat_history(user_prompt: str, history: list):
    if not history:
        history.append({
            "role": "user",
            "content": user_prompt
        })
    return history

def save_chat_message(db: Session, project_id: UUID, role: str, content: str, user_id: UUID = None):
    project_member_id = None
    if user_id:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).first()
        if member:
            project_member_id = member.id
    chat = RequirementChat(
        project_id=project_id,
        role=role,
        content=content,
        project_member_id=project_member_id
    )
    db.add(chat)
    db.commit()
        
def build_initial_user_prompt(db: Session, project_id: UUID, background: str = None) -> str:
    project_detail = get_project_detail(db, project_id)
    project_title = project_detail["project_title"].strip()
    project_description = project_detail["project_description"].strip()
    
    if not background:
        member = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).first()
        if member and member.background:
            background = str(member.background.value) if hasattr(member.background, "value") else str(member.background)
    
    bg_text = background if background else "Unknown"
    
    prompt = USER_PROMPT.format(
        project_title=project_title,
        project_description=project_description,
        technical_background=bg_text
    )
    return prompt

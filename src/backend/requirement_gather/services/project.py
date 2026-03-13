from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID

from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User


def create_project_with_owner(
    db: Session,
    user_id: UUID,
    project_title: str,
    project_description: str,
    background: str
) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    project = Project(
        name=project_title,
        description=project_description,
        status="active",
        created_by=user_id,
    )
    db.add(project)
    db.flush()

    project_member = ProjectMember(
        project_id=project.id,
        user_id=user_id,
        slack_id=None,
        background=background
    )
    db.add(project_member)

    db.commit()
    db.refresh(project)

    return {
        "project_id": str(project.id),
        "project_title": project.name,
        "project_description": project.description or "",
        "background": background
    }

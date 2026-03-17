from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID

from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User


def create_project_with_owner(
    db: Session,
    user_id: UUID,
    project_title: str,
    project_description: str,
    background: str
) -> Project:
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

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
            background=background.lower()
        )
        db.add(project_member)

        db.commit()
        db.refresh(project)

        return project
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to create project: {str(e)}"
        )

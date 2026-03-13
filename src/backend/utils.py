from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.model.project import Project


def get_project_detail(db: Session, project_id: UUID) -> dict | None:
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        return None

    return {
        "project_id": str(project.id),
        "project_title": project.name,
        "project_description": project.description or "",
        "owned_by": str(project.created_by),
    }

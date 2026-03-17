from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.model.project import Project

def build_project_document_title(db: Session, project_id: UUID, label: str) -> str:
    """Helper to build consistent document titles."""
    project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
    return f"{project_title} - {label}"

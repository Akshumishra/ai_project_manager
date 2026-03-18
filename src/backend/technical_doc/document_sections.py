from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.backend.model.project import Project

def build_project_document_title(db: Session, project_id: UUID, document_label: str) -> str:
    project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
    if not project_title:
        raise HTTPException(status_code=404, detail="Project not found")
    return f"{project_title} - {document_label}"

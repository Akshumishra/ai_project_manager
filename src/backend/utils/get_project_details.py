from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.model.project import Project


from src.backend.requirement_gather.constants import RequirementAgentConstants

def get_project_detail(db: Session, project_id: UUID) -> dict | None:
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        return None

    # Find requirement and tech doc IDs
    requirement_doc_id = None
    tech_doc_id = None
    
    # We look for documents with titles containing the labels
    for doc in project.documents:
        if RequirementAgentConstants.REQ_DOC_LABEL in (doc.title or ""):
            requirement_doc_id = str(doc.id)
        # Assuming there will be a tech doc label eventually, but for now just one
        
    return {
        "project_id": str(project.id),
        "project_title": project.name,
        "project_description": project.description or "",
        "owned_by": str(project.created_by),
        "requirement_document_id": requirement_doc_id,
        "tech_document_id": tech_doc_id,
    }

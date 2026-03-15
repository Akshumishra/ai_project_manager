from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.backend.model.document import Document
from src.backend.model.project import Project, ProjectMember


def generate_position(prev_pos, next_pos):
    GAP = 1000.0

    def to_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except ValueError:
            return 0.0

    p = to_float(prev_pos)
    n = to_float(next_pos)

    if p is None and n is None:
        result = GAP
    elif p is None:
        result = n / 2.0
    elif n is None:
        result = p + GAP
    else:
        result = (p + n) / 2.0

    return str(int(result)) if result.is_integer() else str(result)


def verify_document_access(document_id: UUID, user_id: UUID, db: Session):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    project = db.query(Project).filter(Project.id == document.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user_id,
        )
        .first()
    )

    if project.created_by != user_id and not is_member:
        raise HTTPException(
            status_code=403, detail="No access to this document/project"
        )

    return document


def create_blocks_from_text(doc_id: UUID, text: str, db: Session, initial_pos: int = 1000, increment: int = 1000):

    from src.backend.model.document import DocumentBlock
    
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    pos = initial_pos
    for line in lines:
        block = DocumentBlock(
            doc_id=doc_id,
            content=line,
            type="markdown",
            position_key=str(pos)
        )
        db.add(block)
        pos += increment
    
    db.flush()
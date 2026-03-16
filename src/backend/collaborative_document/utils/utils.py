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
            raise HTTPException(status_code=400, detail=f"Invalid position value: {val}")

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
def create_blocks_from_text(doc_id: UUID, text: str, db: Session):
    """
    Parses markdown text into blocks and saves them to the database for a given document.
    """
    from src.backend.model.document import DocumentBlock
    
    # Simple parser: split by double newlines or headers
    import re
    # We split by headers or double newlines to create blocks
    # This is a basic implementation to get things working
    lines = text.split('\n')
    current_block_content = []
    blocks = []
    
    for line in lines:
        if line.startswith('#') or (not line.strip() and current_block_content):
            if current_block_content:
                blocks.append("\n".join(current_block_content).strip())
                current_block_content = []
            if line.strip():
                blocks.append(line.strip())
        else:
            if line.strip() or current_block_content:
                current_block_content.append(line)
                
    if current_block_content:
        blocks.append("\n".join(current_block_content).strip())
        
    # Remove empty blocks
    blocks = [b for b in blocks if b]
    
    if not blocks:
        blocks = ["# New Document"]
        
    # Create blocks with sequential keys
    for i, content in enumerate(blocks):
        block_type = "text"
        if content.startswith('# '): block_type = "h1"
        elif content.startswith('## '): block_type = "h2"
        elif content.startswith('### '): block_type = "h3"
        elif content.startswith('- ') or content.startswith('* '): block_type = "bullet_list"
        
        # Strip header markers from content for some types if desired, 
        # but the editor expects raw markdown for now? 
        # Actually the Editor renders marked(content), so keeping markdown is fine.
        
        new_block = DocumentBlock(
            id=str(uuid.uuid4()) if 'uuid' in globals() else str(__import__('uuid').uuid4()),
            doc_id=doc_id,
            content=content,
            position_key=str((i + 1) * 1000),
            type=block_type
        )
        db.add(new_block)

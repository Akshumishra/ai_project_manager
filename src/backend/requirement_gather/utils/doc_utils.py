import uuid
from sqlalchemy.orm import Session

from src.backend.model.document import Document, DocumentBlock

def save_document(title: str, project_id: uuid.UUID, created_by: uuid.UUID, markdown_content: str, db: Session):
    """
    Locally creates a document and its associated blocks from markdown content.
    """
    document = Document(
        title=title,
        project_id=project_id,
        created_by=created_by
    )
    db.add(document)
    db.flush()
    sync_blocks_from_text(document.id, markdown_content, db)
    
    return {"document_id": str(document.id)}

def sync_blocks_from_text(doc_id: uuid.UUID, text: str, db: Session):
    """
    Clears existing blocks for a document and recreates them by splitting the text.
    """
    db.query(DocumentBlock).filter(DocumentBlock.doc_id == doc_id).delete()
    
    blocks = text.split("\n\n")
    for i, content in enumerate(blocks):
        clean_content = content.strip()
        if not clean_content:
            continue
            
        b_type = "paragraph"
        if clean_content.startswith("#"):
            b_type = "heading"
        
        new_block = DocumentBlock(
            doc_id=doc_id,
            content=clean_content,
            position_key=str((i + 1) * 1000),
            type=b_type
        )
        db.add(new_block)
    
import uuid
from difflib import SequenceMatcher
from typing import List, Dict, Union, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import cast, Float
from fastapi import HTTPException, status
from src.backend.model.document import Document, DocumentBlock, DocumentType
from src.backend.model.project import Project

def generate_position(prev_pos: Optional[str], next_pos: Optional[str]) -> str:
    """
    Generates a numeric string position key between prev_pos and next_pos.
    Uses fractional increments to allow infinite insertions between blocks.
    """
    GAP = 1000.0

    def to_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Invalid position value: {val}"
            )

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


def parse_markdown_blocks(text: str) -> List[Dict[str, str]]:
    """
    Parse markdown text into logical document blocks (h1, h2, h3, bullet_list, text).
    Splits on headings and handles blank lines to keep related lines together.
    """
    lines = text.split("\n")
    current_block_content = []
    blocks = []

    for line in lines:
        if line.startswith("#") or (not line.strip() and current_block_content):
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

    blocks = [b for b in blocks if b]
    if not blocks:
        blocks = ["# New Document"]

    return [
        {
            "content": content,
            "type": _detect_block_type(content),
        }
        for content in blocks
    ]


def sync_blocks_from_text(doc_id: Union[uuid.UUID, str], text: str, db: Session):
    """
    Updates document blocks in the DB based on new markdown text.
    Uses SequenceMatcher to minimize deletions and preserve unchanged blocks.
    """
    
    doc_uuid = uuid.UUID(str(doc_id)) if isinstance(doc_id, str) else doc_id
    desired_blocks = parse_markdown_blocks(text)
    
    existing_blocks = (
        db.query(DocumentBlock)
        .filter(DocumentBlock.doc_id == doc_uuid)
        .order_by(cast(DocumentBlock.position_key, Float))
        .all()
    )

    existing_signatures = [(block.type, block.content) for block in existing_blocks]
    desired_signatures = [(block["type"], block["content"]) for block in desired_blocks]
    matcher = SequenceMatcher(a=existing_signatures, b=desired_signatures)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        existing_slice = existing_blocks[i1:i2]
        desired_slice = desired_blocks[j1:j2]

        if tag == "replace":
            shared = min(len(existing_slice), len(desired_slice))

            for offset in range(shared):
                block = existing_slice[offset]
                desired = desired_slice[offset]
                block.content = desired["content"]
                block.type = desired["type"]

            for block in existing_slice[shared:]:
                db.delete(block)

            if len(desired_slice) > shared:
                _insert_blocks_between(
                    doc_id=doc_uuid,
                    blocks=desired_slice[shared:],
                    prev_block=existing_slice[shared - 1] if shared else _safe_prev_block(existing_blocks, i1),
                    next_block=_safe_next_block(existing_blocks, i2),
                    db=db,
                )

        elif tag == "delete":
            for block in existing_slice:
                db.delete(block)

        elif tag == "insert":
            _insert_blocks_between(
                doc_id=doc_uuid,
                blocks=desired_slice,
                prev_block=_safe_prev_block(existing_blocks, i1),
                next_block=_safe_next_block(existing_blocks, i1),
                db=db,
            )
    
    db.flush()


def _detect_block_type(content: str) -> str:
    """Helper to categorize markdown content into block types."""
    if content.startswith("# "):
        return "h1"
    if content.startswith("## "):
        return "h2"
    if content.startswith("### "):
        return "h3"
    if content.startswith("- ") or content.startswith("* "):
        return "bullet_list"
    return "text"


def _safe_prev_block(blocks, index):
    """Helper to find the preceding block safely during diff application."""
    return blocks[index - 1] if index > 0 and index - 1 < len(blocks) else None


def _safe_next_block(blocks, index):
    """Helper to find the succeeding block safely during diff application."""
    return blocks[index] if index < len(blocks) else None


def _insert_blocks_between(doc_id: uuid.UUID, blocks: List[dict], prev_block, next_block, db: Session):
    """Inserts multiple new blocks between two existing blocks with generated position keys."""
    prev_position = prev_block.position_key if prev_block else None
    next_position = next_block.position_key if next_block else None

    for block in blocks:
        position_key = generate_position(prev_position, next_position)
        db.add(
            DocumentBlock(
                id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=block["content"],
                position_key=position_key,
                type=block["type"],
            )
        )
        prev_position = position_key
def create_blocks_from_text(doc_id: uuid.UUID, text: str, db: Session):
    """
    Creates fresh blocks for a document from markdown text.
    Standardized for core agent features.
    """
    for i, block in enumerate(parse_markdown_blocks(text)):
        db.add(
            DocumentBlock(
                id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=block["content"],
                position_key=str((i + 1) * 1000),
                type=block["type"],
            )
        )


def save_document(
    db: Session,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    markdown_content: str,
    document_type: str = "general"
):
    """
    Standardized service to save a document and its blocks into the database
    for core agent features.
    """
    from src.backend.model.document import Document, DocumentType

    if isinstance(document_type, str):
        try:
            document_type = DocumentType(document_type.lower())
        except ValueError:
            document_type = DocumentType.GENERAL

    document = Document(
        title=title,
        project_id=project_id,
        created_by=user_id,
        document_type=document_type
    )
    db.add(document)
    db.flush()
    sync_blocks_from_text(document.id, markdown_content, db)
    return {"document_id": str(document.id)}


def upsert_document(
    db: Session,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    document_type: str,
    markdown_content: str,
    title_label: Optional[str] = None
) -> Dict[str, Any]:
    """
    Standardized upsert utility for project documents.
    If a document of the given type exists for the project, it updates its blocks.
    Otherwise, it creates a new document.
    """

    if isinstance(document_type, str):
        try:
            norm_type = DocumentType(document_type.lower())
        except ValueError:
            norm_type = DocumentType.GENERAL
    else:
        norm_type = document_type

    existing_doc = db.query(Document).filter(
        Document.project_id == project_id,
        Document.document_type == norm_type,
        Document.deleted_at.is_(None)
    ).first()

    if existing_doc:
        sync_blocks_from_text(existing_doc.id, markdown_content, db)
        doc_id = existing_doc.id
    else:
        if not title_label:
            title_label = str(norm_type.value).title() if hasattr(norm_type, 'value') else str(norm_type).title()
            
        doc_title = build_project_document_title(db, project_id, title_label)
        
        new_doc = Document(
            title=doc_title,
            project_id=project_id,
            created_by=user_id,
            document_type=norm_type
        )
        db.add(new_doc)
        db.flush()
        sync_blocks_from_text(new_doc.id, markdown_content, db)
        doc_id = new_doc.id

    return {
        "status": "success",
        "document_id": str(doc_id),
        "message": f"Document of type '{norm_type.value}' upserted successfully."
    }


def build_project_document_title(db: Session, project_id: uuid.UUID, label: str) -> str:
    """Builds a consistent title for project documents by combining project name and label."""
    try:
        project_title = db.query(Project.name).filter(Project.id == project_id).scalar() or ""
        return f"{project_title} - {label}"
    except Exception as e:
        db.rollback()
        raise e


def get_document_content(db: Session, project_id: uuid.UUID, doc_type: str) -> str:
    """
    Centralized utility to fetch document content by its type (requirement, technical, etc.).
    Returns the concatenated content of all blocks or an empty string if not found.
    """
    try:

        if isinstance(doc_type, str):
            try:
                doc_type = DocumentType(doc_type.lower())
            except ValueError:
                return ""

        doc = db.query(Document).filter(
            Document.project_id == project_id,
            Document.document_type == doc_type
        ).first()

        if not doc:
            return ""

        blocks = db.query(DocumentBlock).filter(
            DocumentBlock.doc_id == doc.id
        ).order_by(DocumentBlock.position_key).all()

        return "\n\n".join(b.content for b in blocks if b.content).strip()
    except Exception as e:
        db.rollback()
        return ""

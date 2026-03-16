from difflib import SequenceMatcher
from uuid import UUID
import uuid
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


def parse_markdown_blocks(text: str) -> list[dict]:
    """
    Parse markdown into logical editor blocks without writing to the database.
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


def create_blocks_from_text(doc_id: UUID, text: str, db: Session):
    """
    Parse markdown text and create fresh blocks for a document.
    """
    from src.backend.model.document import DocumentBlock

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


def sync_blocks_from_text(doc_id: UUID, text: str, db: Session):
    """
    Update only changed blocks for a document while preserving unchanged ones.
    """
    from src.backend.model.document import DocumentBlock

    desired_blocks = parse_markdown_blocks(text)
    existing_blocks = (
        db.query(DocumentBlock)
        .filter(DocumentBlock.doc_id == doc_id)
        .order_by(DocumentBlock.position_key)
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
                    doc_id=doc_id,
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
                doc_id=doc_id,
                blocks=desired_slice,
                prev_block=_safe_prev_block(existing_blocks, i1),
                next_block=_safe_next_block(existing_blocks, i1),
                db=db,
            )


def _detect_block_type(content: str) -> str:
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
    return blocks[index - 1] if index > 0 and index - 1 < len(blocks) else None


def _safe_next_block(blocks, index):
    return blocks[index] if index < len(blocks) else None


def _insert_blocks_between(doc_id: UUID, blocks: list[dict], prev_block, next_block, db: Session):
    from src.backend.model.document import DocumentBlock

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

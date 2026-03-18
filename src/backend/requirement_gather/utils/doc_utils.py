import uuid
import difflib
from typing import List
from sqlalchemy.orm import Session

from src.backend.model.document import Document, DocumentBlock


def _parse_markdown_to_blocks(text: str) -> List[dict]:
    """
    Parses markdown text into a list of block dicts with 'content' and 'type'.
    Splits on headings and blank lines — same logic as technical_doc/doc_sync.py.
    """
    lines = text.split('\n')
    current_block_content: List[str] = []
    blocks: List[str] = []

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

    blocks = [b for b in blocks if b]
    if not blocks:
        blocks = ["# New Document"]

    parsed_blocks = []
    for content in blocks:
        block_type = "text"
        if content.startswith('# '):
            block_type = "h1"
        elif content.startswith('## '):
            block_type = "h2"
        elif content.startswith('### '):
            block_type = "h3"
        elif content.startswith('- ') or content.startswith('* '):
            block_type = "bullet_list"
        parsed_blocks.append({"content": content, "type": block_type})

    return parsed_blocks


def save_document(title: str, project_id: uuid.UUID, created_by: uuid.UUID, markdown_content: str, db: Session):
    """
    Creates a new document and its associated blocks from markdown content.
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
    Differentially updates document blocks from new markdown text.
    Uses difflib.SequenceMatcher to only update changed blocks —
    unchanged blocks are left untouched (no delete + reinsert).
    """
    from sqlalchemy import cast, Float

    # 1. Parse new content into blocks
    new_parsed = _parse_markdown_to_blocks(text)
    new_contents = [b["content"] for b in new_parsed]

    # 2. Get existing blocks ordered numerically by position_key
    old_blocks = db.query(DocumentBlock).filter(
        DocumentBlock.doc_id == doc_id
    ).order_by(cast(DocumentBlock.position_key, Float)).all()
    old_contents = [b.content for b in old_blocks]

    # 3. Compute diff and build the final sequence of blocks
    sm = difflib.SequenceMatcher(None, old_contents, new_contents)
    final_blocks: List = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            # Unchanged blocks — keep them, only update type if it changed
            for idx in range(i1, i2):
                old_blk = old_blocks[idx]
                new_blk_data = new_parsed[j1 + (idx - i1)]
                if old_blk.type != new_blk_data["type"]:
                    old_blk.type = new_blk_data["type"]
                final_blocks.append(old_blk)
        elif tag == 'replace':
            # Replace changed blocks (soft: skip marking deleted_at since DocumentBlock has none)
            for idx in range(i1, i2):
                db.delete(old_blocks[idx])
            for idx in range(j1, j2):
                new_data = new_parsed[idx]
                new_blk = DocumentBlock(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=new_data["content"],
                    type=new_data["type"]
                )
                db.add(new_blk)
                final_blocks.append(new_blk)
        elif tag == 'delete':
            # Remove blocks that are no longer present
            for idx in range(i1, i2):
                db.delete(old_blocks[idx])
        elif tag == 'insert':
            # Add brand-new blocks
            for idx in range(j1, j2):
                new_data = new_parsed[idx]
                new_blk = DocumentBlock(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=new_data["content"],
                    type=new_data["type"]
                )
                db.add(new_blk)
                final_blocks.append(new_blk)

    # 4. Assign temporary keys to avoid unique constraint conflicts during re-ordering
    for block in final_blocks:
        block.position_key = f"tmp_{uuid.uuid4()}"
    db.flush()

    # 5. Re-assign final sequential position keys
    for i, block in enumerate(final_blocks):
        block.position_key = str((i + 1) * 1000)
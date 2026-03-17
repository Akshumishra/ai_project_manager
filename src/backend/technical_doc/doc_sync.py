from uuid import UUID
import uuid
from sqlalchemy.orm import Session
import difflib

def _parse_markdown_to_blocks(text: str):
    import re
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
        
    blocks = [b for b in blocks if b]
    
    # If no blocks are parsed, add a default H1 block
    if not blocks:
        blocks = ["# New Document"]
    
    parsed_blocks = []
    for content in blocks:
        block_type = "text"
        if content.startswith('# '): block_type = "h1"
        elif content.startswith('## '): block_type = "h2"
        elif content.startswith('### '): block_type = "h3"
        elif content.startswith('- ') or content.startswith('* '): block_type = "bullet_list"
        parsed_blocks.append({"content": content, "type": block_type})
        
    return parsed_blocks


def sync_blocks_from_text(doc_id: UUID, text: str, db: Session):
    """
    Differentially updates document blocks based on new markdown text.
    """
    from src.backend.model.document import DocumentBlock
    from sqlalchemy import cast, Float

    # 1. Parse new content
    new_parsed = _parse_markdown_to_blocks(text)
    new_contents = [b["content"] for b in new_parsed]

    # 2. Get existing blocks ordered numerically by position_key
    old_blocks = db.query(DocumentBlock).filter(
        DocumentBlock.doc_id == doc_id
    ).order_by(cast(DocumentBlock.position_key, Float)).all()
    old_contents = [b.content for b in old_blocks]

    # 3. Use SequenceMatcher to find differences
    sm = difflib.SequenceMatcher(None, old_contents, new_contents)
    
    final_blocks = [] # List of block objects in order

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            # Blocks are same, keep them
            for idx in range(i1, i2):
                old_blk = old_blocks[idx]
                new_blk_data = new_parsed[j1 + (idx - i1)]
                # update type if it changed (content is equal)
                if old_blk.type != new_blk_data["type"]:
                    old_blk.type = new_blk_data["type"]
                final_blocks.append(old_blk)
        elif tag == 'replace':
            # Delete old ones, insert new ones
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
            # Remove old blocks
            for idx in range(i1, i2):
                db.delete(old_blocks[idx])
        elif tag == 'insert':
            # Add new blocks
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

    # To avoid unique constraint violations (uq_doc_position: doc_id, position_key)
    # when re-assigning keys, we first give them all a temporary unique key.
    # We prefix with a very large number or just use their UUID.
    for block in final_blocks:
        block.position_key = f"tmp_{uuid.uuid4()}"
    
    db.flush() # Ensure deletions and temp keys are flushed to DB

    # 4. Re-calculate final position keys for the sequence
    for i, block in enumerate(final_blocks):
        block.position_key = str((i + 1) * 1000)

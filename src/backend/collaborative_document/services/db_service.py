from sqlalchemy.orm import Session
from sqlalchemy import cast, Float
from uuid import UUID
from fastapi import HTTPException
from src.backend.model.document import Document, DocumentBlock

def get_document_by_id(db: Session, doc_id: UUID):
    return db.query(Document).filter(Document.id == doc_id).first()

def get_document_blocks(db: Session, doc_id: UUID):
    return (
        db.query(DocumentBlock)
        .filter(DocumentBlock.doc_id == doc_id)
        .order_by(cast(DocumentBlock.position_key, Float))
        .all()
    )

def create_block(db: Session, block_id: str, doc_id: UUID, key: str, content: str, block_type: str):
    block = DocumentBlock(id=block_id, doc_id=doc_id, position_key=key, content=content, type=block_type)
    db.add(block)
    db.commit()
    return block

def get_block_by_id(db: Session, block_id: str):
    return db.query(DocumentBlock).filter(DocumentBlock.id == block_id).first()

def delete_block_db(db: Session, block_id: str):
    db.query(DocumentBlock).filter(DocumentBlock.id == block_id).delete()
    db.commit()

def update_block_db(db: Session, block_id: str, content: str, block_type: str = None):
    block = get_block_by_id(db, block_id)
    if not block:
        raise HTTPException(404, "Block not found")
    block.content = content
    if block_type is not None:
        block.type = block_type
    db.commit()
    return block

def get_block_position_db(db: Session, block_id: str):
    block = get_block_by_id(db, block_id)
    return block.position_key if block else None

def delete_document_db(db: Session, doc_id: UUID):
    doc = get_document_by_id(db, doc_id)
    if doc:
        db.delete(doc)
        db.commit()
        return True
    return False

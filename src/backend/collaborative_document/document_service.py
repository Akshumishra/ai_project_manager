from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
import uuid
import time
import redis

from .utils import utils
from . import schemas
from src.backend.collaborative_document.routes.websocket import manager
from src.backend.model.document import Document, DocumentBlock
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User

from .services import cache_service, db_service

def create_document(data: schemas.DocumentCreate, db: Session, current_user: User):
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == data.project_id,
            ProjectMember.user_id == current_user.id,
        )
        .first()
    )

    if project.created_by != current_user.id and not is_member:
        raise HTTPException(
            status_code=403, detail="No access to create documents in this project"
        )

    document = Document(
        title=data.title, project_id=data.project_id, created_by=current_user.id
    )
    db.add(document)
    db.flush()

    block = DocumentBlock(doc_id=document.id, position_key="1000")
    db.add(block)
    db.commit()
    return {"document_id": str(document.id), "initial_block_id": str(block.id)}


def save_document(
    data: schemas.DocumentCreate,
    markdown_content: str,
    db: Session,
    current_user: User
):
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == data.project_id,
            ProjectMember.user_id == current_user.id,
        )
        .first()
    )

    if project.created_by != current_user.id and not is_member:
        raise HTTPException(
            status_code=403, detail="No access to create documents in this project"
        )

    document = Document(
        title=data.title, project_id=data.project_id, created_by=current_user.id
    )
    db.add(document)
    db.flush()

    utils.create_blocks_from_text(document.id, markdown_content, db)
    db.commit()
    return {"document_id": str(document.id)}


def get_document(document_id: UUID, db: Session, current_user: User):
    utils.verify_document_access(document_id, current_user.id, db)
    
    cached = cache_service.get_cached_document(document_id)
    if cached:
        return cached

    document = db_service.get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    blocks = db_service.get_document_blocks(db, document_id)
    result_blocks = [
        {
            "block_id": str(b.id),
            "position_key": b.position_key,
            "content": b.content,
            "type": b.type,
        }
        for b in blocks
    ]

    response = {
        "document_id": str(document_id),
        "title": document.title,
        "blocks": result_blocks,
    }
    
    cache_service.set_cached_document(document_id, response)
    return response


async def insert_block(
    document_id: UUID, data: schemas.BlockCreate, db: Session, current_user: User
):
    utils.verify_document_access(document_id, current_user.id, db)
    if not db_service.get_document_by_id(db, document_id):
        raise HTTPException(404, "Document not found")

    new_id = str(uuid.uuid4())
    new_key = data.position_key or _calculate_position(document_id, data.prev_block_id, data.next_block_id, db)

    block_data = {
        "block_id": new_id,
        "position_key": new_key,
        "content": data.content,
        "type": data.type,
    }

    try:
        cache_service.buffer_block_insert(new_id, document_id, block_data)
        cache_service.update_block_in_cache(document_id, block_data)
    except (redis.ConnectionError, redis.TimeoutError):
        db_service.create_block(db, new_id, document_id, new_key, data.content, data.type)

    await _broadcast_update(document_id, "insert", {"block": block_data, "client_id": data.client_id})
    return {"block_id": new_id, "position_key": new_key, "client_id": data.client_id}


async def edit_block(block_id: str, data: schemas.BlockUpdate, db: Session, current_user: User):
    block = db_service.get_block_by_id(db, block_id)
    if not block:
        raise HTTPException(404, "Block not found")

    utils.verify_document_access(block.doc_id, current_user.id, db)

    try:
        cache_service.buffer_block_update(block_id, data.content, data.type)
        cache_service.update_block_in_cache(block.doc_id, {"block_id": block_id, "content": data.content, "type": data.type})
    except (redis.ConnectionError, redis.TimeoutError):
        db_service.update_block_db(db, block_id, data.content, data.type)
        
    return {"message": "updated"}


async def delete_block(block_id: str, db: Session, current_user: User):
    doc_id = _find_doc_id_for_block(block_id, db)
    utils.verify_document_access(doc_id, current_user.id, db)

    # Check if it's still in the insert buffer
    if cache_service.get_pending_insert_pos(block_id):
        cache_service.clear_pending_insert(block_id)
    else:
        try:
            cache_service.buffer_block_delete(block_id)
        except (redis.ConnectionError, redis.TimeoutError):
            db_service.delete_block_db(db, block_id)

    cache_service.remove_block_from_cache(doc_id, block_id)
    await _broadcast_update(doc_id, "delete", {"block_id": block_id})
    return {"message": "Block deleted"}


def update_document(document_id: UUID, data: schemas.DocumentUpdate, db: Session, current_user: User):
    utils.verify_document_access(document_id, current_user.id, db)
    document = db_service.get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(404, "Document not found")

    document.title = data.title
    db.commit()
    db.refresh(document)
    cache_service.sync_title_to_cache(document_id, document.title)
    return document


def delete_document(document_id: UUID, db: Session, current_user: User):
    utils.verify_document_access(document_id, current_user.id, db)
    if db_service.delete_document_db(db, document_id):
        cache_service.delete_doc_cache(document_id)
        return {"message": "Document deleted"}
    raise HTTPException(404, "Document not found")


def _calculate_position(doc_id: UUID, prev_id: str | None, next_id: str | None, db: Session) -> str:
    prev_key = _get_block_position(prev_id, db) if prev_id else None
    next_key = _get_block_position(next_id, db) if next_id else None
    return utils.generate_position(prev_key, next_key)


def _get_block_position(block_id: str, db: Session) -> str:
    # Try cache first (pending inserts)
    pos = cache_service.get_pending_insert_pos(block_id)
    if pos:
        return pos
    
    # Then DB
    pos = db_service.get_block_position_db(db, block_id)
    if pos:
        return pos
    
    raise HTTPException(400, f"Block {block_id} not found")


def _find_doc_id_for_block(block_id: str, db: Session) -> UUID:
    doc_id = cache_service.get_pending_insert_doc_id(block_id)
    if doc_id:
        return doc_id
    
    block = db_service.get_block_by_id(db, block_id)
    if not block:
        raise HTTPException(404, "Block not found")
    return block.doc_id


async def _broadcast_update(doc_id: UUID, update_type: str, payload: dict):
    message = {"type": update_type, "timestamp": time.time(), **payload}
    await manager.broadcast_to_doc(str(doc_id), message)
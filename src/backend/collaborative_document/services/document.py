from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy import cast, Float
from uuid import UUID
import uuid
import json, time, redis

from src.backend.collaborative_document.utils import helper_function
from src.backend.collaborative_document import schemas
from src.backend.collaborative_document.routes.websocket import manager
from src.backend.db.redis import redis_client
from src.backend.model.document import Document, DocumentBlock
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User


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


def get_document(document_id: UUID, db: Session, current_user: User):
    helper_function.verify_document_access(document_id, current_user.id, db)
    redis_key = f"doc:{document_id}"
    cached = redis_client.get(redis_key)
    if cached:
        doc_data = json.loads(cached)
        if "title" in doc_data:
            return doc_data

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    blocks = (
        db.query(DocumentBlock)
        .filter(DocumentBlock.doc_id == document_id)
        .order_by(cast(DocumentBlock.position_key, Float))
        .all()
    )

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
    redis_client.set(redis_key, json.dumps(response), ex=3000)
    return response


async def insert_block(
    document_id: UUID, data: schemas.BlockCreate, db: Session, current_user: User
):
    helper_function.verify_document_access(document_id, current_user.id, db)
    _verify_document_exists(document_id, db)

    new_id = uuid.uuid4()
    new_key = data.position_key or _calculate_position(document_id, data.prev_block_id, data.next_block_id, db)

    block_data = {
        "block_id": str(new_id),
        "position_key": new_key,
        "content": data.content,
        "type": data.type,
    }

    # Redis-buffered Insert
    try:
        redis_client.set(f"pending_insert:{new_id}", json.dumps({"doc_id": str(document_id), **block_data}), ex=3600)
        redis_client.sadd("pending_inserts", new_id)
        _update_doc_cache(document_id, block_data)
    except (redis.ConnectionError, redis.TimeoutError):
        _persist_block_to_db(new_id, document_id, new_key, data, db)

    await _broadcast_update(document_id, "insert", {"block": block_data, "client_id": data.client_id})
    
    return {"block_id": new_id, "position_key": new_key, "client_id": data.client_id}


async def edit_block(block_id: str, data: schemas.BlockUpdate, db: Session, current_user: User):
    block = db.query(DocumentBlock).filter(DocumentBlock.id == block_id).first()
    if not block:
        raise HTTPException(404, "Block not found")

    helper_function.verify_document_access(block.doc_id, current_user.id, db)

    try:
        redis_client.set(f"block_update:{block_id}", json.dumps({"content": data.content, "type": data.type}))
        redis_client.zadd("dirty_blocks", {block_id: time.time()})
        _update_doc_cache(block.doc_id, {"block_id": block_id, "content": data.content, "type": data.type})
    except (redis.ConnectionError, redis.TimeoutError):
        block.content = data.content
        if data.type is not None:
            block.type = data.type
        db.commit()
        
    return {"message": "updated"}


async def delete_block(block_id: str, db: Session, current_user: User):
    doc_id = _find_doc_id_for_block(block_id, db)
    helper_function.verify_document_access(doc_id, current_user.id, db)

    # 1. Handle Pending Insert
    is_pending = False
    try:
        is_pending = redis_client.exists(f"pending_insert:{block_id}")
    except (redis.ConnectionError, redis.TimeoutError):
        pass # Fallback to trying delete in DB
        
    if is_pending:
        redis_client.srem("pending_inserts", block_id)
        redis_client.delete(f"pending_insert:{block_id}")
    else:
        # 2. Handle Persisted Block
        try:
            redis_client.sadd("pending_deletes", block_id)
        except (redis.ConnectionError, redis.TimeoutError):
            db.query(DocumentBlock).filter(DocumentBlock.id == block_id).delete()
            db.commit()

    _remove_from_doc_cache(doc_id, block_id)
    await _broadcast_update(doc_id, "delete", {"block_id": block_id})
    return {"message": "Block deleted"}


def update_document(document_id: UUID, data: schemas.DocumentUpdate, db: Session, current_user: User):
    helper_function.verify_document_access(document_id, current_user.id, db)
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")

    document.title = data.title
    db.commit()
    db.refresh(document)
    _sync_title_to_cache(document_id, document.title)
    return document


def delete_document(document_id: UUID, db: Session, current_user: User):
    helper_function.verify_document_access(document_id, current_user.id, db)
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")

    db.delete(document)
    db.commit()
    redis_client.delete(f"doc:{document_id}")
    return {"message": "Document deleted"}


# --- Private Helpers ---

def _verify_document_exists(doc_id: UUID, db: Session):
    if not db.query(Document).filter(Document.id == doc_id).first():
        raise HTTPException(404, "Document not found")


def _calculate_position(doc_id: UUID, prev_id: str | None, next_id: str | None, db: Session) -> str:
    prev_key = _get_block_position(prev_id, db) if prev_id else None
    next_key = _get_block_position(next_id, db) if next_id else None
    return helper_function.generate_position(prev_key, next_key)


def _get_block_position(block_id: str, db: Session) -> str:
    block = db.query(DocumentBlock).filter(DocumentBlock.id == block_id).first()
    if block:
        return block.position_key
    
    cached = redis_client.get(f"pending_insert:{block_id}")
    if cached:
        return json.loads(cached).get("position_key")
    
    raise HTTPException(400, f"Block {block_id} not found")


def _persist_block_to_db(block_id: UUID | str, doc_id: UUID, key: str, data: schemas.BlockCreate, db: Session):
    b_uuid = UUID(str(block_id)) if isinstance(block_id, str) else block_id
    block = DocumentBlock(id=b_uuid, doc_id=doc_id, position_key=key, content=data.content, type=data.type)
    db.add(block)
    db.commit()


def _update_doc_cache(doc_id: UUID, block_update: dict):
    redis_key = f"doc:{doc_id}"
    cached = redis_client.get(redis_key)
    if not cached:
        return

    doc_data = json.loads(cached)
    # Update existing or add new
    found = False
    for b in doc_data["blocks"]:
        if b["block_id"] == block_update["block_id"]:
            b.update(block_update)
            found = True
            break
    
    if not found:
        doc_data["blocks"].append(block_update)
    
    doc_data["blocks"].sort(key=lambda x: float(x["position_key"]))
    
    ttl = redis_client.ttl(redis_key)
    if ttl and ttl > 0:
        redis_client.setex(redis_key, ttl, json.dumps(doc_data))
    else:
        redis_client.set(redis_key, json.dumps(doc_data), ex=3000)


def _remove_from_doc_cache(doc_id: UUID, block_id: str):
    redis_key = f"doc:{doc_id}"
    cached = redis_client.get(redis_key)
    if not cached:
        return
    
    doc_data = json.loads(cached)
    doc_data["blocks"] = [b for b in doc_data["blocks"] if b["block_id"] != block_id]
    
    ttl = redis_client.ttl(redis_key)
    if ttl and ttl > 0:
        redis_client.setex(redis_key, ttl, json.dumps(doc_data))
    else:
        redis_client.set(redis_key, json.dumps(doc_data), ex=3000)


def _find_doc_id_for_block(block_id: str, db: Session) -> UUID:
    # Check Redis first
    cached = redis_client.get(f"pending_insert:{block_id}")
    if cached:
        return UUID(json.loads(cached)["doc_id"])
    
    # Fallback to DB
    block = db.query(DocumentBlock).filter(DocumentBlock.id == block_id).first()
    if not block:
        raise HTTPException(404, "Block not found")
    return block.doc_id


def _sync_title_to_cache(doc_id: UUID, title: str):
    redis_key = f"doc:{doc_id}"
    cached = redis_client.get(redis_key)
    if not cached:
        return
    
    try:
        doc_data = json.loads(cached)
        doc_data["title"] = title
        
        ttl = redis_client.ttl(redis_key)
        if ttl and ttl > 0:
            redis_client.setex(redis_key, ttl, json.dumps(doc_data))
        else:
            redis_client.set(redis_key, json.dumps(doc_data), ex=3000)
    except Exception:
        redis_client.delete(redis_key)


async def _broadcast_update(doc_id: UUID, update_type: str, payload: dict):
    message = {"type": update_type, "timestamp": time.time(), **payload}
    await manager.broadcast_to_doc(str(doc_id), message)

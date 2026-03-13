from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy import cast, Float
from sqlalchemy.exc import IntegrityError
from uuid import UUID
import json, time, random, redis

from . import schemas, utils, websocket
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
    utils.verify_document_access(document_id, current_user.id, db)
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


async def insert_block(document_id: UUID, data: schemas.BlockCreate, db: Session, current_user: User):
    utils.verify_document_access(document_id, current_user.id, db)
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")

    prev_key = None
    next_key = None
    if data.prev_block_id:
        prev_block = (
            db.query(DocumentBlock)
            .filter(
                DocumentBlock.id == data.prev_block_id,
                DocumentBlock.doc_id == document_id,
            )
            .first()
        )
        if not prev_block:
            raise HTTPException(400, "Invalid prev_block_id")
        prev_key = prev_block.position_key

    if data.next_block_id:
        next_block = (
            db.query(DocumentBlock)
            .filter(
                DocumentBlock.id == data.next_block_id,
                DocumentBlock.doc_id == document_id,
            )
            .first()
        )
        if not next_block:
            raise HTTPException(400, "Invalid next_block_id")
        next_key = next_block.position_key

    new_key = utils.generate_position(prev_key, next_key)
    MAX_RETRIES = 5
    for attempt in range(MAX_RETRIES):
        try:
            block = DocumentBlock(
                doc_id=document_id,
                position_key=new_key,
                content=data.content,
                type=data.type,
            )
            db.add(block)
            db.commit()
            break
        except IntegrityError:
            db.rollback()
            if attempt == MAX_RETRIES - 1:
                raise HTTPException(500, "Concurrency collision")
            new_key = str(float(new_key) + random.uniform(0.0001, 0.0099))

    block_data = {
        "block_id": str(block.id),
        "position_key": block.position_key,
        "content": block.content,
        "type": block.type,
    }
    redis_key = f"doc:{document_id}"
    cached = redis_client.get(redis_key)
    if cached:
        doc_data = json.loads(cached)
        doc_data["blocks"].append(block_data)
        doc_data["blocks"].sort(key=lambda x: x["position_key"])
        redis_client.set(redis_key, json.dumps(doc_data))

    await websocket.manager.broadcast_to_doc(
        str(document_id),
        {
            "type": "insert",
            "block": block_data,
            "client_id": data.client_id,
            "timestamp": time.time(),
        },
    )
    return {
        "block_id": str(block.id),
        "position_key": block.position_key,
        "client_id": data.client_id,
    }


async def edit_block(block_id: str, data: schemas.BlockUpdate, db: Session, current_user: User):
    block = db.query(DocumentBlock).filter(DocumentBlock.id == block_id).first()
    if not block:
        raise HTTPException(404, "Block not found")
    
    utils.verify_document_access(block.doc_id, current_user.id, db)
    
    doc_id = block.doc_id
    try:
        redis_client.set(
            f"block_update:{block_id}",
            json.dumps({"content": data.content, "type": data.type}),
        )
        redis_client.zadd("dirty_blocks", {str(block_id): time.time()})
        redis_key = f"doc:{doc_id}"
        cached = redis_client.get(redis_key)
        if cached:
            doc_data = json.loads(cached)
            for b in doc_data["blocks"]:
                if b["block_id"] == block_id:
                    b["content"] = data.content
                    if data.type is not None:
                        b["type"] = data.type
                    break
            redis_client.set(redis_key, json.dumps(doc_data))
    except (redis.ConnectionError, redis.TimeoutError):
        block.content = data.content
        if data.type is not None:
            block.type = data.type
        db.commit()
    return {"message": "updated"}


async def delete_block(block_id: str, db: Session, current_user: User):
    block = db.query(DocumentBlock).filter(DocumentBlock.id == block_id).first()
    if not block:
        raise HTTPException(404, "Block not found")
    
    utils.verify_document_access(block.doc_id, current_user.id, db)
    
    doc_id = block.doc_id
    db.delete(block)
    db.commit()
    redis_key = f"doc:{doc_id}"
    cached = redis_client.get(redis_key)
    if cached:
        doc_data = json.loads(cached)
        doc_data["blocks"] = [
            b for b in doc_data["blocks"] if b["block_id"] != block_id
        ]
        redis_client.set(redis_key, json.dumps(doc_data))
    await websocket.manager.broadcast_to_doc(
        str(doc_id), {"type": "delete", "block_id": block_id, "timestamp": time.time()}
    )
    return {"message": "Block deleted"}

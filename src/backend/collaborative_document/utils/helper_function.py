from sqlalchemy import cast, Float
from difflib import SequenceMatcher
from uuid import UUID
import uuid
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src.backend.db.database import get_session_local
from src.backend.model.document import Document,DocumentBlock
from src.backend.model.project import Project, ProjectMember


def generate_position(prev_pos, next_pos):
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


def verify_document_access(document_id: UUID, user_id: UUID, db: Session):
    document = db.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Document not found"
        )

    project = db.query(Project).filter(Project.id == document.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Project not found"
        )

    is_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user_id,
        )
        .first()
    )

    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No access to this document/project"
        )

    return document

def fetch_init_data_sync(doc_uuid):
    from src.backend.db.redis import redis_client
    with get_session_local()() as db:
        document = db.query(Document).filter(Document.id == doc_uuid).first()
        if document:
            blocks = (
                db.query(DocumentBlock)
                .filter(DocumentBlock.doc_id == doc_uuid, DocumentBlock.deleted_at.is_(None))
                .order_by(cast(DocumentBlock.position_key, Float))
                .all()
            )
            block_list = []
            for b in blocks:
                block_data = {
                    "block_id": str(b.id),
                    "position_key": b.position_key,
                    "content": b.content,
                    "type": b.type,
                }
                # Overlay any pending Redis edits that haven't been flushed to DB yet
                pending_edit = redis_client.get(f"block_update:{b.id}")
                if pending_edit:
                    try:
                        edit = json.loads(pending_edit)
                        block_data["content"] = edit.get("content", block_data["content"])
                        if edit.get("type"):
                            block_data["type"] = edit["type"]
                    except json.JSONDecodeError:
                        pass
                block_list.append(block_data)

            # Also include pending inserts that haven't been flushed to DB yet
            pending_insert_ids = redis_client.smembers("pending_inserts") or set()
            for pid in pending_insert_ids:
                insert_json = redis_client.get(f"pending_insert:{pid}")
                if insert_json:
                    try:
                        insert_data = json.loads(insert_json)
                        if insert_data.get("doc_id") == str(doc_uuid):
                            if not any(b["block_id"] == insert_data["block_id"] for b in block_list):
                                block_data = {
                                    "block_id": insert_data["block_id"],
                                    "position_key": insert_data["position_key"],
                                    "content": insert_data.get("content", ""),
                                    "type": insert_data.get("type", "paragraph"),
                                }
                                # Overlay any pending edits typed after block creation
                                pending_edit = redis_client.get(f"block_update:{insert_data['block_id']}")
                                if pending_edit:
                                    try:
                                        edit = json.loads(pending_edit)
                                        block_data["content"] = edit.get("content", block_data["content"])
                                        if edit.get("type"):
                                            block_data["type"] = edit["type"]
                                    except json.JSONDecodeError:
                                        pass
                                block_list.append(block_data)
                    except json.JSONDecodeError:
                        pass

            block_list.sort(key=lambda x: float(x["position_key"]))

            return {
                "document_id": str(doc_uuid),
                "title": document.title,
                "blocks": block_list,
            }
        return {"error": "Document not found."}

def check_block_sync(block_id, doc_uuid):
    with get_session_local()() as db:
        return db.query(DocumentBlock).filter(
            DocumentBlock.id == block_id,
            DocumentBlock.doc_id == doc_uuid
        ).first() is not None

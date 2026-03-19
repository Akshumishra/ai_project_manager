from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import json, time
from jose import jwt, JWTError
from uuid import UUID
from sqlalchemy import cast, Float
import logging

logger = logging.getLogger(__name__)

from src.backend.db.database import get_session_local
from src.backend.model.document import Document, DocumentBlock
from src.backend.db.redis import redis_client
from src.backend.config import settings
from src.backend.collaborative_document.services.websocket import ConnectionManager
from src.backend.collaborative_document.utils import helper_function
import asyncio

def fetch_init_data_sync(doc_uuid):
    with get_session_local()() as db:
        document = db.query(Document).filter(Document.id == doc_uuid).first()
        if document:
            blocks = (
                db.query(DocumentBlock)
                .filter(DocumentBlock.doc_id == doc_uuid)
                .order_by(cast(DocumentBlock.position_key, Float))
                .all()
            )
            return {
                "document_id": str(doc_uuid),
                "title": document.title,
                "blocks": [
                    {
                        "block_id": str(b.id),
                        "position_key": b.position_key,
                        "content": b.content,
                        "type": b.type,
                    }
                    for b in blocks
                ],
            }
        return {"error": "Document not found."}

def check_block_sync(block_id, doc_uuid):
    with get_session_local()() as db:
        return db.query(DocumentBlock).filter(
            DocumentBlock.id == block_id,
            DocumentBlock.doc_id == doc_uuid
        ).first() is not None

manager = ConnectionManager()

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/{document_id}")
async def websocket_endpoint(
    websocket: WebSocket, document_id: str, token: str = Query(None)
):
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    try:
        payload = jwt.decode(
            token, settings.ACCESS_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("user_id")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token content")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    connection_id = None
    try:
        doc_uuid = UUID(str(document_id))
        user_uuid = UUID(str(user_id))
        with get_session_local()() as db:
            helper_function.verify_document_access(doc_uuid, user_uuid, db)
    except Exception as e:
        await websocket.close(code=1008, reason=f"Access denied: {str(e)}")
        return

    connection_id, role = await manager.connect(websocket, document_id, user_id)

    try:
        cached = redis_client.get(f"doc:{doc_uuid}")
        init_data = None
        if cached:
            try:
                init_data = json.loads(cached)
            except json.JSONDecodeError:
                pass
                
        if not init_data:
            init_data = await asyncio.to_thread(fetch_init_data_sync, doc_uuid)
            if "error" not in init_data:
                redis_client.set(f"doc:{doc_uuid}", json.dumps(init_data), ex=3000)
 
        await websocket.send_json({"type": "init", "role": role, "data": init_data})

        while True:
            msg_text = await websocket.receive_text()
            try:
                data = json.loads(msg_text)
            except json.JSONDecodeError:
                continue

            if data.get("type") == "edit":
                if role != "editor":
                    await websocket.send_json({"type": "error", "message": "View-only mode: Editor limit reached (30)."})
                    continue

                block_id = data.get("block_id")
                content = data.get("content")
                block_type = data.get("block_type", "paragraph")
                
                if not block_id or content is None:
                    await websocket.send_json({"type": "error", "message": "Invalid edit payload"})
                    continue
                    
                edit_timestamp = time.time()

                try:
                    # Validate block belongs to document asynchronously safely
                    block_exists = await asyncio.to_thread(check_block_sync, block_id, doc_uuid)
                    
                    if not block_exists:
                        pending = redis_client.get(f"pending_insert:{block_id}")
                        if not pending:
                            await websocket.send_json({"type": "error", "message": "Unauthorized block edit"})
                            continue
                        try:
                            if json.loads(pending).get("doc_id") != str(doc_uuid):
                                await websocket.send_json({"type": "error", "message": "Unauthorized block edit"})
                                continue
                        except json.JSONDecodeError:
                            continue

                    redis_client.setex(
                        f"block_update:{block_id}",
                        86400, # Expire after 24 hrs preventing memory leaks
                        json.dumps({"content": content, "type": block_type}),
                    )
                    redis_client.zadd("dirty_blocks", {str(block_id): edit_timestamp})
                    
                    # Prevent race condition by completely erasing doc cache so the next full page load pulls safely from the DB rather than corrupting a giant nested JSON
                    redis_client.delete(f"doc:{doc_uuid}")
                except Exception as e:
                    logger.error(f"Redis write error on websocket edit: {str(e)}")

                broadcast_msg = {
                    "type": "update",
                    "block_id": block_id,
                    "content": content,
                    "block_type": block_type,
                    "timestamp": edit_timestamp,
                }
                await manager.broadcast_to_doc(
                    str(doc_uuid), broadcast_msg, sender_id=connection_id
                )

            else:
                await websocket.send_json({"type": "error", "message": "Unknown message type"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket unhandled error: {e}")
    finally:
        if connection_id:
            manager.disconnect(connection_id, document_id)

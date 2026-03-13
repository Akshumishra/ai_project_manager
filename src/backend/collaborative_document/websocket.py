from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict
import json, time
from jose import jwt, JWTError
from uuid import UUID
from sqlalchemy import cast, Float

from src.backend.db.database import SessionLocal
from src.backend.model.document import Document, DocumentBlock
from src.backend.db.redis import redis_client
from src.backend.config import Config


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[WebSocket, str]] = {}
        self.MAX_EDITORS = 30

    async def connect(self, websocket: WebSocket, document_id: str, user_id: str):
        await websocket.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id] = {}
        self.active_connections[document_id][websocket] = user_id
        role = (
            "editor"
            if len(self.active_connections[document_id]) <= self.MAX_EDITORS
            else "viewer"
        )
        return role

    def disconnect(self, websocket: WebSocket, document_id: str):
        if document_id in self.active_connections:
            if websocket in self.active_connections[document_id]:
                del self.active_connections[document_id][websocket]
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]

    async def broadcast_to_doc(
        self, document_id: str, message: dict, exclude: WebSocket = None
    ):
        if document_id in self.active_connections:
            for connection in list(self.active_connections[document_id].keys()):
                if connection != exclude:
                    try:
                        await connection.send_json(message)
                    except WebSocketDisconnect:
                        self.disconnect(connection, document_id)


manager = ConnectionManager()

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/{document_id}")
async def websocket_endpoint(
    websocket: WebSocket, document_id: str, token: str = Query(None)
):
    if not token:
        await websocket.accept()
        await websocket.close(code=1008, reason="Missing token")
        return

    try:
        payload = jwt.decode(
            token, Config.ACCESS_SECRET_KEY, algorithms=[Config.ALGORITHM]
        )
        user_id = payload.get("user_id")
        if not user_id:
            await websocket.accept()
            await websocket.close(code=1008, reason="Invalid token content")
            return
    except JWTError:
        await websocket.accept()
        await websocket.close(code=1008, reason="Invalid token")
        return

    role = await manager.connect(websocket, document_id, user_id)

    try:
        doc_uuid = UUID(str(document_id))
        cached = redis_client.get(f"doc:{doc_uuid}")
        if cached:
            init_data = json.loads(cached)
        else:
            with SessionLocal() as db:
                document = db.query(Document).filter(Document.id == doc_uuid).first()
                if document:
                    blocks = (
                        db.query(DocumentBlock)
                        .filter(DocumentBlock.doc_id == document_id)
                        .order_by(cast(DocumentBlock.position_key, Float))
                        .all()
                    )
                    init_data = {
                        "document_id": str(document_id),
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
                    redis_client.set(
                        f"doc:{document_id}", json.dumps(init_data), ex=3000
                    )
                else:
                    init_data = {"error": "Document not found."}

        await websocket.send_json({"type": "init", "role": role, "data": init_data})

        while True:
            msg_text = await websocket.receive_text()
            try:
                data = json.loads(msg_text)
            except json.JSONDecodeError:
                continue

            if data.get("type") == "edit":
                if role != "editor":
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "View-only mode: Editor limit reached (30).",
                        }
                    )
                    continue

                block_id = data.get("block_id")
                content = data.get("content")
                block_type = data.get("block_type", "paragraph")
                edit_timestamp = time.time()

                try:
                    redis_client.set(
                        f"block_update:{block_id}",
                        json.dumps({"content": content, "type": block_type}),
                    )
                    redis_client.zadd("dirty_blocks", {str(block_id): edit_timestamp})
                    cached_doc = redis_client.get(f"doc:{document_id}")
                    if cached_doc:
                        doc_data = json.loads(cached_doc)
                        for b in doc_data["blocks"]:
                            if b["block_id"] == block_id:
                                b["content"] = content
                                b["type"] = block_type
                                break
                        redis_client.set(f"doc:{document_id}", json.dumps(doc_data))
                except Exception as e:
                    print(f"Redis write error on websocket edit: {e}")

                broadcast_msg = {
                    "type": "update",
                    "block_id": block_id,
                    "content": content,
                    "block_type": block_type,
                    "timestamp": edit_timestamp,
                }
                await manager.broadcast_to_doc(
                    document_id, broadcast_msg, exclude=websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, document_id)

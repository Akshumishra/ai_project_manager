import asyncio
import json
import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any

# Create a global async redis client for PubSub
redis_async = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[WebSocket, str]] = {}
        self.pubsub_tasks: Dict[str, asyncio.Task] = {}
        self.MAX_EDITORS = 30

    async def connect(self, websocket: WebSocket, document_id: str, user_id: str):
        await websocket.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id] = {}
        
        # Count existing editors
        current_editors = sum(1 for role in self.active_connections[document_id].values() if role == "editor")
        
        role = "editor" if current_editors < self.MAX_EDITORS else "viewer"
        self.active_connections[document_id][websocket] = role
        
        # Start listening to Redis pubsub for this document if not already doing so
        if document_id not in self.pubsub_tasks:
            task = asyncio.create_task(self._listen_to_redis(document_id))
            self.pubsub_tasks[document_id] = task

        return role

    async def _listen_to_redis(self, document_id: str):
        pubsub = redis_async.pubsub()
        channel_name = f"doc_channel:{document_id}"
        await pubsub.subscribe(channel_name)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    payload = data.get("payload")
                    sender_id = data.get("sender_id")
                    
                    # Broadcast to all local connections for this document
                    for connection in list(self.active_connections.get(document_id, {}).keys()):
                        # We use id(connection) to exclude the sender if they are on the same worker
                        if str(id(connection)) != sender_id:
                            try:
                                await connection.send_json(payload)
                            except Exception:
                                self.disconnect(connection, document_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"PubSub error for {document_id}: {e}")
        finally:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()

    def disconnect(self, websocket: WebSocket, document_id: str):
        if document_id in self.active_connections:
            if websocket in self.active_connections[document_id]:
                del self.active_connections[document_id][websocket]
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]
                # Stop the pubsub task when no local clients remain
                if document_id in self.pubsub_tasks:
                    self.pubsub_tasks[document_id].cancel()
                    del self.pubsub_tasks[document_id]

    async def broadcast_to_doc(
        self, document_id: str, message: dict, exclude: WebSocket = None
    ):
        # Publish the message to Redis so it reaches all workers
        data = {
            "payload": message,
            "sender_id": str(id(exclude)) if exclude else None
        }
        await redis_async.publish(f"doc_channel:{document_id}", json.dumps(data))
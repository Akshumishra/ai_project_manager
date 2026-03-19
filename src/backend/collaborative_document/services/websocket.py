import asyncio
import json
import uuid
import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any
import logging
from src.backend.config import settings

logger = logging.getLogger(__name__)

# Create a global async redis client for PubSub
redis_async = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True)

class ConnectionManager:
    def __init__(self):
        # Maps document_id -> { connection_id: {"websocket": WebSocket, "role": str, "user_id": str} }
        self.active_connections: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.pubsub_tasks: Dict[str, asyncio.Task] = {}
        self.MAX_EDITORS = 30

    async def connect(self, websocket: WebSocket, document_id: str, user_id: str) -> tuple[str, str]:
        await websocket.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id] = {}
        
        # Count existing editors safely using the new dictionary structure
        current_editors = sum(1 for meta in self.active_connections[document_id].values() if meta["role"] == "editor")
        
        role = "editor" if current_editors < self.MAX_EDITORS else "viewer"
        
        # Generate a globally unique connection ID so cross-worker messaging actually works blindly
        connection_id = str(uuid.uuid4())
        
        self.active_connections[document_id][connection_id] = {
            "websocket": websocket,
            "role": role,
            "user_id": user_id
        }
        
        # Start listening to Redis pubsub for this document if not already doing so
        if document_id not in self.pubsub_tasks:
            task = asyncio.create_task(self._listen_to_redis(document_id))
            self.pubsub_tasks[document_id] = task

        return connection_id, role

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
                    
                    # Safely convert to list to prevent "dictionary changed size during iteration" race conditions
                    connections = list(self.active_connections.get(document_id, {}).items())
                    for conn_id, meta in connections:
                        # Exclude the sender using the globally unique connection UUID, preventing identical echoes across workers
                        if conn_id != sender_id:
                            try:
                                await meta["websocket"].send_json(payload)
                            except Exception as e:
                                logger.error(f"Error sending message to {conn_id}: {e}")
                                self.disconnect(conn_id, document_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"PubSub error for {document_id}: {str(e)}")
        finally:
            try:
                await pubsub.unsubscribe(channel_name)
                # Use standard .aclose() to safely close async redis bindings preventing memory leaks
                await pubsub.aclose()
            except Exception as e:
                logger.error(f"Failed to cleanly close PubSub for {document_id}: {e}")

    def disconnect(self, connection_id: str, document_id: str):
        try:
            if document_id in self.active_connections:
                if connection_id in self.active_connections[document_id]:
                    del self.active_connections[document_id][connection_id]
                
                # Stop the pubsub task when no local clients remain
                if not self.active_connections[document_id]:
                    del self.active_connections[document_id]
                    if document_id in self.pubsub_tasks:
                        self.pubsub_tasks[document_id].cancel()
                        del self.pubsub_tasks[document_id]
        except Exception as e:
            logger.error(f"Safe disconnect failed for {connection_id}: {e}")

    async def broadcast_to_doc(
        self, document_id: str, message: dict, sender_id: str = None
    ):
        # Publish the message to Redis so it reaches all workers natively
        data = {
            "payload": message,
            "sender_id": sender_id
        }
        await redis_async.publish(f"doc_channel:{document_id}", json.dumps(data))
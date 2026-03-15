from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict


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
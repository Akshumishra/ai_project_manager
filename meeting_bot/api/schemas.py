from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class JoinRequest(BaseModel):
    url: str
    max_duration: Optional[int] = None
    audio_device: Optional[str] = None


class MultiJoinRequest(BaseModel):
    urls: List[str]
    max_duration: Optional[int] = None
    audio_device: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    url: str


class StatusResponse(BaseModel):
    active_sessions: List[dict]
    count: int

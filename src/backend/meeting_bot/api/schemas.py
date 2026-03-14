from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, field_validator


class JoinRequest(BaseModel):
    url: str
    max_duration: Optional[int] = None
    audio_device: Optional[str] = None

    @field_validator("audio_device")
    @classmethod
    def filter_placeholder(cls, v: Optional[str]) -> Optional[str]:
        if v == "string":
            return None
        return v


class MultiJoinRequest(BaseModel):
    urls: List[str]
    max_duration: Optional[int] = None
    audio_device: Optional[str] = None

    @field_validator("audio_device")
    @classmethod
    def filter_placeholder(cls, v: Optional[str]) -> Optional[str]:
        if v == "string":
            return None
        return v


class SessionResponse(BaseModel):
    session_id: str
    url: str


class StatusResponse(BaseModel):
    active_sessions: List[dict]
    count: int

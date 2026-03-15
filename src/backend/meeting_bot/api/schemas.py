from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class JoinRequest(BaseModel):
    url: str
    max_duration: Optional[int] = None
    audio_device: Optional[str] = None

    # ── Optional DB metadata ───────────────────────────────────────────────────
    # When provided, the bot will persist a Meeting record to the database.
    # project_id and created_by must both be present for DB writes to occur.
    project_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    title: Optional[str] = None
    task_id: Optional[UUID] = None     # Escalation trigger from Module 2
    agenda: Optional[str] = None

    @field_validator("audio_device")
    @classmethod
    def filter_placeholder(cls, v: Optional[str]) -> Optional[str]:
        return None if v == "string" else v


class MultiJoinRequest(BaseModel):
    urls: List[str]
    max_duration: Optional[int] = None
    audio_device: Optional[str] = None

    # Shared DB metadata applied to all sessions in the batch.
    project_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    agenda: Optional[str] = None

    @field_validator("audio_device")
    @classmethod
    def filter_placeholder(cls, v: Optional[str]) -> Optional[str]:
        return None if v == "string" else v


class SessionResponse(BaseModel):
    session_id: str
    url: str


class StatusResponse(BaseModel):
    active_sessions: List[dict]
    count: int

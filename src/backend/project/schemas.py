from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: Optional[str]
    created_by: UUID
    created_at: datetime


class AddMemberRequest(BaseModel):
    email: str


class MessageResponse(BaseModel):
    message: str

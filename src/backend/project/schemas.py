from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class ProjectCreateRequest(BaseModel):
    name: str
    description: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    created_by: UUID
    created_at: datetime


class AddMemberRequest(BaseModel):
    email: str


class MessageResponse(BaseModel):
    message: str


class ProjectDocumentResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime

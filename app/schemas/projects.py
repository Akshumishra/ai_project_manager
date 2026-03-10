from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProjectCreate(BaseModel):
    project_name: str
    project_description: Optional[str] = None
    workspace_id: str

class ProjectResponse(BaseModel):
    project_id: UUID
    project_name: str
    project_description: Optional[str] = None
    workspace_id: str
    channel_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    channel_id: Optional[str] = None
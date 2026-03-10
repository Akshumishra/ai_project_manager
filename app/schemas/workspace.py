from pydantic import BaseModel
from typing import Optional


class WorkspaceCreate(BaseModel):
    workspace_id: str
    workspace_name: str
    invite_link: str


class WorkspaceResponse(BaseModel):
    workspace_id: str
    workspace_name: str
    invite_link: str

    class Config:
        from_attributes = True


class WorkspaceUpdate(BaseModel):
    workspace_name: Optional[str] = None
    invite_link: Optional[str] = None
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    background: Optional[str] = "technical"


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: Optional[str]
    created_by: UUID
    created_at: datetime


class ProjectWorkflowStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workflow_name: str
    status: str


class ProjectStatusRead(BaseModel):
    project_id: UUID
    workflows: List[ProjectWorkflowStatusRead]


class AddMemberRequest(BaseModel):
    email: str


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    complexity: Optional[str] = "medium"
    deadline: Optional[datetime] = None
    project_member_id: Optional[UUID] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    complexity: Optional[str] = None
    deadline: Optional[datetime] = None
    project_member_id: Optional[UUID] = None
    status: Optional[str] = None


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    status: str
    assignee_name: Optional[str] = None


class MemberRead(BaseModel):
    id: UUID
    name: str
    email: str
    status: str

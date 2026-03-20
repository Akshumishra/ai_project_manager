from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    background: Optional[str] = "technical"


class ProjectStatusUpdate(BaseModel):
    status: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: Optional[str]
    status: str
    slack_channel_id: Optional[str] = None
    created_by: UUID
    created_at: datetime


class SlackChannelResponse(BaseModel):
    slack_url: str


class SlackChannelSetRequest(BaseModel):
    slack_channel_id: str


class ProjectWorkflowStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workflow_name: str
    status: str


class ProjectStatusRead(BaseModel):
    project_id: UUID
    workflows: List[ProjectWorkflowStatusRead]


class AddMemberRequest(BaseModel):
    email: str
    background: Optional[str] = "technical"



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
    label: Optional[int] = None
    assignee_name: Optional[str] = None

class TaskLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    log: str
    created_at: datetime


class StandupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    message_ts: str
    prompt: Optional[str]
    summary: Optional[str]
    created_at: datetime


class MemberRead(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    email: str
    status: str

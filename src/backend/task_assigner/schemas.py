from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from src.backend.schemas.common import AgentRequest, StandardResponse


class TaskAssignerAgentRequest(AgentRequest):
    message: Optional[str] = None


class TaskAssignment(BaseModel):
    task_id: UUID
    member_id: UUID
    deadline: datetime


class AssignTasksRequest(BaseModel):
    user_id: UUID
    project_id: UUID
    assignments: List[TaskAssignment]


class TaskAssignerResponseSchema(BaseModel):
    status: str
    message: Optional[str] = None
    messages: Optional[list] = None
    thinking: Optional[bool] = False
    redirect: Optional[str] = None

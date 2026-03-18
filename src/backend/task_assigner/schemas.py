from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional


class TaskAssignerAgentRequest(BaseModel):
    user_id: UUID
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


class StandardResponse(BaseModel):
    success: bool
    message: str

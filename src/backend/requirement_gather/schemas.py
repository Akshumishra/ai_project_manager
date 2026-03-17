from pydantic import BaseModel
from uuid import UUID
from typing import Any, List, Dict

class CreateProjectRequest(BaseModel):
    user_id: UUID
    project_title: str
    project_description: str
    background: str


class RequirementAgentRequest(BaseModel):
    user_id: UUID
    message: str


class SaveRequirementRequest(BaseModel):
    user_id: UUID
    problem_the_project_solves: str
    target_users: str
    project_goal: str
    key_system_capabilities: str
    expected_outcome: str
    major_constraints: str
    additional_notes: str


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    status: str | None = None
    created_by: UUID
    requirement_document_id: UUID | str | None = None
    tech_document_id: UUID | str | None = None

    model_config = {"from_attributes": True}


class RequirementAgentResponse(BaseModel):
    content: str | None = ""
    document: str | None = ""
    saved: bool | None = False
    document_id: UUID | None = None
    status: str | None = None
    messages: List[Dict[str, Any]] | None = None
    thinking: bool | None = False


class StandardResponse(BaseModel):
    status: str
    message: str

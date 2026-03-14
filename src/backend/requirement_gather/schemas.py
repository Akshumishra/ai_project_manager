from pydantic import BaseModel
from uuid import UUID

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

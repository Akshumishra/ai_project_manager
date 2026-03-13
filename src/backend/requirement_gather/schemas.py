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

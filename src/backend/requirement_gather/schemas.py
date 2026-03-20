from pydantic import BaseModel
from uuid import UUID
from typing import Any, List, Dict
from src.backend.schemas.common import AgentRequest, StandardResponse

class RequirementAgentRequest(AgentRequest):
    pass


class RequirementAgentResponse(BaseModel):
    content: str | None = ""
    document: str | None = ""
    saved: bool | None = False
    status: str | None = None
    messages: List[Dict[str, Any]] | None = None
    thinking: bool | None = False

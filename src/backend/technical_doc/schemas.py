from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from src.backend.schemas.common import AgentRequest, StandardResponse

class TechDocAgentRequest(AgentRequest):
    current_document_markdown: Optional[str] = None

class SaveTechDocRequest(BaseModel):
    user_id: UUID
    document_markdown: str

class TechDocResponseSchema(BaseModel):
    status: str
    content: Optional[str] = None
    message: Optional[str] = None
    document: Optional[str] = None

    messages: Optional[list] = None
    thinking: Optional[bool] = False
    saved: Optional[bool] = False
    redirect: Optional[str] = None

class TechDocSaveResponseSchema(StandardResponse):
    pass


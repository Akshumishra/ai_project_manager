from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class TechDocAgentRequest(BaseModel):
    user_id: UUID
    message: str
    current_document_markdown: Optional[str] = None

class SaveTechDocRequest(BaseModel):
    user_id: UUID
    document_markdown: str

class TechDocResponseSchema(BaseModel):
    status: str
    message: Optional[str] = None
    document: Optional[str] = None
    messages: Optional[list] = None
    thinking: Optional[bool] = False
    redirect: Optional[str] = None

class TechDocSaveResponseSchema(BaseModel):
    status: str
    message: str

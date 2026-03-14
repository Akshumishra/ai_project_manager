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

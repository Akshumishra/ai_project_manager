from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from src.backend.schemas.common import AgentRequest, StandardResponse


class TaskAssignerResponseSchema(BaseModel):
    status: str
    content: Optional[str] = None
    messages: Optional[list] = None
    thinking: Optional[bool] = False
    redirect: Optional[str] = None

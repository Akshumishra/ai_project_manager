from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List, Dict, Any

class StandardResponse(BaseModel):
    status: str
    message: str

class AgentRequest(BaseModel):
    user_id: Optional[UUID] = None
    message: str

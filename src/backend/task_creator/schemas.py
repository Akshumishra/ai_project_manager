from pydantic import BaseModel

class TaskGenerationResponse(BaseModel):
    status: str
    message: str

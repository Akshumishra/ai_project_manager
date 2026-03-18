from pydantic import BaseModel, Field
from typing import List


class ResumeExtraction(BaseModel):
    skills: List[str] = Field(
        description="List of technical skills mentioned in the resume"
    )
    yoe: int = Field(description="Total years of professional experience (YOE)")
    designation: str = Field(description="Current or most recent job title")


class MessageResponse(BaseModel):
    message: str

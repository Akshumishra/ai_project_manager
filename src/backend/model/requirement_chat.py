from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel


class RequirementChat(BaseModel):
    __tablename__ = "requirement_chats"
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    project_member_id = Column(UUID(as_uuid=True), nullable=True)

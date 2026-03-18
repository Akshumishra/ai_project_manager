from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel


class RequirementChat(BaseModel):
    __tablename__ = "requirement_chats"
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    project_member_id = Column(
        UUID(as_uuid=True), ForeignKey("project_members.id"), nullable=True
    )

    project = relationship("Project", back_populates="requirement_chats")

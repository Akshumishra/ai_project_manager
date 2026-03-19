from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.backend.model.base import BaseModel


class TaskAssignerChat(BaseModel):
    __tablename__ = "task_assigner_chats"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    project_member_id = Column(UUID(as_uuid=True), ForeignKey("project_members.id"), nullable=True)

from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone

from src.backend.model.base import BaseModel


class Blocker(BaseModel):
    __tablename__ = "blockers"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    reason = Column(Text, nullable=False)
    blocked_by = Column(String, nullable=True)
    impact = Column(String, nullable=True) # e.g., 'high', 'low'
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project")
    user = relationship("User")
    task = relationship("Task")

    def __repr__(self):
        return f"<Blocker(id={self.id}, user='{self.user_id}', task='{self.task_id}', reason='{self.reason[:20]}...')>"

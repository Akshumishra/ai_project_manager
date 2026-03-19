from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel


class TaskLog(BaseModel):
    __tablename__ = "task_logs"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    log = Column(Text, nullable=False)

    task = relationship("Task", back_populates="logs")
import enum
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    INPROGRESS = "inprogress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class Task(BaseModel):
    __tablename__ = "tasks"

    name = Column(String, nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=True)
    complexity = Column(String, nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(TaskStatus, name="task_status_enum"),
        nullable=False,
        default=TaskStatus.TODO,
    )
    project_member_id = Column(
        UUID(as_uuid=True), ForeignKey("project_members.id"), nullable=True
    )

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("ProjectMember", back_populates="tasks")

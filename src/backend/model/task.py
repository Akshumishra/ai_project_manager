import enum
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum, Integer, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel

class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskCategory(str, enum.Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    AI_ML = "ai_ml"
    DEVOPS = "devops"
    QA = "qa"
    SECURITY = "security"


class TaskComplexity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(BaseModel):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "label", name="uq_project_task_label"),
    )

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False
    )

    title = Column(String, nullable=False)
    label = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)

    category = Column(
        Enum(TaskCategory, name="task_category_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    priority = Column(
        Enum(TaskPriority, name="task_priority_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TaskPriority.MEDIUM
    )

    complexity = Column(
        Enum(TaskComplexity, name="task_complexity_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TaskComplexity.MEDIUM
    )

    story_points = Column(Integer, nullable=True)

    estimated_hours = Column(Integer, nullable=True)

    deadline = Column(DateTime(timezone=True), nullable=True)
    ai_generated = Column(Boolean, default=True)

    status = Column(
        Enum(TaskStatus, name="task_status_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TaskStatus.TODO
    )

    project_member_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_members.id"),
        nullable=True
    )

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("ProjectMember", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

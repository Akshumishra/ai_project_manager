import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Integer, DateTime, Text
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


class TaskComplexity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskCategory(str, enum.Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    AI_ML = "ai_ml"
    DEVOPS = "devops"
    QA = "qa"
    SECURITY = "security"


class Task(BaseModel):
    __tablename__ = "tasks"

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
        index=True
    )

    title = Column(
        String,
        nullable=False
    )

    label = Column(
        Integer,
        nullable=False
    )
    
    description = Column(
        Text,
        nullable=True
    )

    category = Column(
        Enum(TaskCategory, name="task_category_enum"),
        nullable=False
    )

    priority = Column(
        Enum(TaskPriority, name="task_priority_enum"),
        nullable=False,
        default=TaskPriority.MEDIUM
    )

    complexity = Column(
        Enum(TaskComplexity, name="task_complexity_enum"),
        nullable=False,
        default=TaskComplexity.MEDIUM
    )

    status = Column(
        Enum(TaskStatus, name="task_status_enum"),
        nullable=False,
        default=TaskStatus.TODO
    )

    due_date = Column(
        DateTime,
        nullable=True
    )

    project_member_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_members.id"),
        nullable=True,
        index=True
    )

    project = relationship(
        "Project",
        back_populates="tasks"
    )

    assignee = relationship(
        "ProjectMember",
        back_populates="tasks"
    )
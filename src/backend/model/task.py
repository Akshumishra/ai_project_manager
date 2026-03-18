import enum
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum, Integer, Boolean
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

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
        index=True
    )

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    label = Column(Integer, nullable=False)
    category = Column(
        Enum(TaskCategory, name="task_category_enum"),
        nullable=False,
        default=TaskCategory.BACKEND
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
    deadline = Column(DateTime, nullable=True)

    project_member_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_members.id"),
        nullable=True,
        index=True
    )

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("ProjectMember", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")


from sqlalchemy import event, func


@event.listens_for(Task, "before_insert")
def set_next_label(mapper, connection, target):
    """
    Automatically sets the next sequential label for a project before inserting a new task.
    This ensures that labels are always sequential per project, regardless of how they are created.
    """
    if target.label is not None and target.label > 0:
        return

    # Using the connection to execute a raw SQL query to get the max label for the project.
    from src.backend.model.task import Task as TaskModel
    from sqlalchemy.orm import object_session
    
    # Construct the query to get max label from DB
    table = TaskModel.__table__
    query = table.select().with_only_columns(func.max(table.c.label)).where(table.c.project_id == target.project_id)
    
    db_max = connection.execute(query).scalar() or 0
    
    # Also check the current session for other tasks that haven't been flushed/committed yet
    session = object_session(target)
    session_max = 0
    if session:
        for obj in session.new:
            if isinstance(obj, TaskModel) and obj.project_id == target.project_id and obj != target:
                if obj.label and obj.label > session_max:
                    session_max = obj.label
    
    target.label = max(db_max, session_max) + 1

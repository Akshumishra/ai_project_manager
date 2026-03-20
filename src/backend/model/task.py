import enum
from sqlalchemy import Column, String, ForeignKey, Enum, Integer, DateTime
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

    description = Column(
        String,
        nullable=True
    )

    label = Column(
        Integer,
        nullable=False
    )

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

    status = Column(
        Enum(TaskStatus, name="task_status_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TaskStatus.TODO
    )

    deadline = Column(
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

    logs = relationship(
        "TaskLog",
        back_populates="task",
        cascade="all, delete-orphan"
    )


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

    table = TaskModel.__table__	
    query = table.select().with_only_columns(func.max(table.c.label)).where(table.c.project_id == target.project_id)	

    db_max = connection.execute(query).scalar() or 0	

    session = object_session(target)	
    session_max = 0	
    if session:	
        for obj in session.new:	
            if isinstance(obj, TaskModel) and obj.project_id == target.project_id and obj != target:	
                if obj.label and obj.label > session_max:	
                    session_max = obj.label	

    target.label = max(db_max, session_max) + 1	

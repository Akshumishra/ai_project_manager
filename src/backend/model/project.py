from sqlalchemy import Column, String, Text, ForeignKey, Enum, UniqueConstraint
import enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel

class Background(str, enum.Enum):
    TECHNICAL = "technical"
    NON_TECHNICAL = "non_technical"

class ProjectStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    HOLD = "hold"

class WorkflowStatus(enum.Enum):
    IN_PROGRESS = "in_progress"
    THINKING = "thinking"
    COMPLETED = "completed"

class Project(BaseModel):
    __tablename__ = "projects"

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(ProjectStatus, name="projectstatus", values_callable=lambda x: [e.value for e in x]), 
        default=ProjectStatus.ACTIVE,
        nullable=False
    )
    slack_channel_id = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    creator = relationship("User", back_populates="projects", foreign_keys=[created_by])
    slack_details = relationship(
        "ProjectSlackDetail", back_populates="project", cascade="all, delete-orphan"
    )
    members = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    documents = relationship(
        "Document", back_populates="project", cascade="all, delete-orphan"
    )
    standups = relationship(
        "Standup", back_populates="project", cascade="all, delete-orphan"
    )
    requirement_chats = relationship(
        "RequirementChat", back_populates="project", cascade="all, delete-orphan"
    )
    tech_doc_chats = relationship(
        "TechDocChat", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectSlackDetail(BaseModel):
    __tablename__ = "project_slack_details"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    workspace_id = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)
    bot_token = Column(String, nullable=True)

    project = relationship("Project", back_populates="slack_details")


class ProjectMember(BaseModel):
    __tablename__ = "project_members"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    slack_id = Column(String, nullable=True)
    background = Column(
        Enum(Background, name="background_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="memberships")
    tasks = relationship("Task", back_populates="assignee")


class ProjectWorkflowStatus(BaseModel):
    __tablename__ = "project_workflow_status"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    workflow_name = Column(String, nullable=False)
    status = Column(
        Enum(WorkflowStatus, name="workflowstatus", values_callable=lambda x: [e.value for e in x]), 
        default=WorkflowStatus.IN_PROGRESS,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("project_id", "workflow_name", name="unique_project_workflow"),
    )

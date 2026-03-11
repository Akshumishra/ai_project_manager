from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.app.model.base import BaseModel


class Project(BaseModel):
    __tablename__ = "projects"

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    creator = relationship("User", back_populates="projects", foreign_keys=[created_by])
    stack_details = relationship(
        "ProjectSlackDetail", back_populates="project", cascade="all, delete-orphan"
    )
    members = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    documents = relationship(
        "Document", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectSlackDetail(BaseModel):
    __tablename__ = "project_slack_details"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    workspace_id = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)
    bot_token = Column(String, nullable=True)

    project = relationship("Project", back_populates="stack_details")


class ProjectMember(BaseModel):
    __tablename__ = "project_members"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    slack_id = Column(String, nullable=True)

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="memberships")
    tasks = relationship("Task", back_populates="assignee")
    requirement_chats = relationship("RequirementChat", back_populates="project_member")

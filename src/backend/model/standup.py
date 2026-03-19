from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel


class Standup(BaseModel):
    __tablename__ = "standups"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    slack_channel_id = Column(String, nullable=True)
    message_ts = Column(String, nullable=False, index=True)
    prompt = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    project = relationship("Project", back_populates="standups")
    updates = relationship(
        "StandupUpdate", back_populates="standup", cascade="all, delete-orphan"
    )

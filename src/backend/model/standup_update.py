from sqlalchemy import Column, Text, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel


class StandupUpdate(BaseModel):
    __tablename__ = "standup_updates"

    standup_id = Column(UUID(as_uuid=True), ForeignKey("standups.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reply_text = Column(Text, nullable=False)
    slack_ts = Column(String, nullable=True, unique=True)

    standup = relationship("Standup", back_populates="updates")
    user = relationship("User")
    action_logs = relationship(
        "StandupActionLog", back_populates="update", cascade="all, delete-orphan"
    )

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel


class StandupActionLog(BaseModel):
    __tablename__ = "standup_action_logs"

    update_id = Column(
        UUID(as_uuid=True), ForeignKey("standup_updates.id"), nullable=False
    )
    action_taken = Column(String, nullable=False)

    update = relationship("StandupUpdate", back_populates="action_logs")

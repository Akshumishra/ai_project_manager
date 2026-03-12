from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel


class UserDetail(BaseModel):
    __tablename__ = "user_details"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )
    skills = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)
    designation = Column(String, nullable=True)
    slack_id = Column(String, nullable=True)

    user = relationship("User", back_populates="detail")

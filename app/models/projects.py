import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base  # your SQLAlchemy Base

class Project(Base):
    __tablename__ = "projects"

    project_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_name = Column(String, unique=True, nullable=False)
    project_description = Column(Text, nullable=True)
    workspace_id = Column(String, nullable=False)
    channel_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
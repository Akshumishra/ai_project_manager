import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base 
# from sqlalchemy.ext.declarative import declarative_base

# Base = declarative_base()

class ChannelMapping(Base):
    __tablename__ = "channel_mapping"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    channel_id = Column(String(50), unique=True, nullable=False)
    channel_name = Column(String(100), nullable=False)
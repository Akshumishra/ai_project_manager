import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base 
# from sqlalchemy.ext.declarative import declarative_base

# Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False)
    slack_id = Column(String(50), unique=True, nullable=True)
    email_id = Column(String(100), unique=True, nullable=False)
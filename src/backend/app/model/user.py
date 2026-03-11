from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from src.backend.app.model.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
   

    detail = relationship(
        "UserDetail", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    projects = relationship(
        "Project", back_populates="creator", foreign_keys="Project.created_by"
    )
    memberships = relationship("ProjectMember", back_populates="user")

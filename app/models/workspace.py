from sqlalchemy import Column, String, Text
from app.database import Base


class Workspace(Base):

    __tablename__ = "workspaces"

    workspace_id = Column(String, primary_key=True)
    workspace_name = Column(String, nullable=False)
    invite_link = Column(Text, nullable=False)
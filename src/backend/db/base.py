from src.backend.db.database import Base

# Import all models so Alembic and SQLAlchemy can detect them
from src.backend.model.user import User
from src.backend.model.user_detail import UserDetail
from src.backend.model.document import Document, DocumentBlock
from src.backend.model.project import (
    Project,
    ProjectSlackDetail,
    ProjectMember,
)
from src.backend.model.task import Task
from src.backend.model.requirement_chat import RequirementChat

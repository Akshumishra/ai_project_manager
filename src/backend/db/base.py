from src.backend.db.database import Base

# Import all models so Alembic and SQLAlchemy can detect them
from src.backend.model.user import User
from src.backend.model.user_detail import UserDetail
from src.backend.model.document import Document, DocumentBlock
from src.backend.model.project import (
    Project,
    ProjectSlackDetail,
    ProjectMember,
    ProjectWorkflowStatus,
)
from src.backend.model.task import Task
from src.backend.model.requirement_chat import RequirementChat
from src.backend.model.meeting import (
    Meeting,
    MeetingParticipant,
    MeetingTranscript,
    MeetingSummary,
    MeetingActionItem,
)
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.task_log import TaskLog

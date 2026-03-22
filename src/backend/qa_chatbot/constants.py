from sqlalchemy import select, bindparam
from src.backend.config import settings
from src.backend.model.project import ProjectSlackDetail, ProjectMember

class SlackConstants:
    POST_MESSAGE_URL = f"{settings.SLACK_API_BASE_URL}/chat.postMessage"
    CONVERSATIONS_REPLIES_URL = f"{settings.SLACK_API_BASE_URL}/conversations.replies"
    MAX_TS_HISTORY = 1000
    API_TIMEOUT = 10

class QAAgentConstants:
    MODEL = "gpt-4o-mini"
    TEMPERATURE = 0.7
    
    SAFE_COLUMNS = {
        "id", "name", "email", "slack_id", "created_at", "updated_at",
        "user_id", "skills", "experience", "designation",
        "project_id", "description", "status", "created_by",
        "workspace_id", "channel_id",
        "doc_id", "title", "content", "position_key", "type",
        "complexity", "deadline", "project_member_id", "role",
        "label", "category", "priority",
        "total_tasks", "assigned_to", "count", "num_tasks",
        "slack_channel_id", "message_ts", "prompt", "summary",
        "reply_text", "slack_ts", "action_taken", "update_id", "standup_id",
        "meet_url", "bot_session_id", "meeting_type", "agenda", "scheduled_at",
        "started_at", "ended_at", "meeting_id", "invite_source", "invite_reason",
        "role_in_meeting", "joined_at", "left_at", "raw_text", "segments",
        "word_count", "summary_text", "key_decisions", "risks_and_blockers",
        "ai_model", "generated_at", "source_quote", "assigned_to_member_id", "due_date"
    }

class QAQueries:
    GET_PROJECT_ID_BY_CHANNEL = select(ProjectSlackDetail.project_id).where(
        ProjectSlackDetail.channel_id == bindparam("channel_id"),
        ProjectSlackDetail.deleted_at.is_(None)
    ).limit(1)
    
    GET_PROJECT_MEMBER_ID = select(ProjectMember.id).where(
        ProjectMember.project_id == bindparam("project_id"),
        ProjectMember.slack_id == bindparam("slack_id"),
        ProjectMember.deleted_at.is_(None)
    ).limit(1)

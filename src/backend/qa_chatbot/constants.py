from src.backend.config import settings

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
        "reply_text", "slack_ts", "action_taken", "update_id", "standup_id"
    }

class QAQueries:
    GET_PROJECT_ID_BY_CHANNEL = """
        SELECT project_id
        FROM project_slack_details
        WHERE channel_id = :channel_id
          AND deleted_at IS NULL
        LIMIT 1
    """
    
    GET_PROJECT_MEMBER_ID = """
        SELECT id
        FROM project_members
        WHERE project_id = :project_id
          AND slack_id   = :slack_id
          AND deleted_at IS NULL
        LIMIT 1
    """

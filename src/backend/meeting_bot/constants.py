from typing import Dict, List

FIREFLIES_API_BASE_URL: str = "https://api.fireflies.ai/graphql"
FIREFLIES_FETCH_TIMEOUT: float = 30.0

SLACK_MEET_EPHEMERAL_SCHEDULING_MSG: str = "⏳  **Scheduling meeting, please hold...**"
SLACK_MEETING_SUCCESS_TEMPLATE: str = (
    "✅  *Google Meet Space Scheduled!*\n"
    "📅  **Title**: {title}\n"
    "⏳  **Duration**: {duration_minutes} minutes\n"
    "🔗  **Join link**: {meet_url}\n"
    "📝  **Agenda**: {agenda}"
)

DEFAULT_MEETING_DURATION_MINS: int = 45
MIN_MEETING_DURATION_MINS: int = 5
MAX_MEETING_DURATION_MINS: int = 480
DEFAULT_MEET_URL: str = "https://meet.google.com"
FIREFLIES_BOT_EMAIL: str = "fred@fireflies.ai"
IST_TIMEZONE_OFFSET_HOURS: int = 5
IST_TIMEZONE_OFFSET_MINS: int = 30
SCHEDULE_MEETING_OFFSET_MINS: int = 2
BOT_SESSION_ID_PREFIX: str = "ffl-"
DEFAULT_TRANSCRIPT_LANGUAGE: str = "en"

DEFAULT_AI_MODEL: str = "gpt-4o"
DEFAULT_AI_TEMPERATURE: float = 0.1
AGENT_MAX_ITERATIONS: int = 5

TASK_STATUS_IN_PROGRESS: str = "in_progress"
TASK_STATUS_TODO: str = "todo"
TASK_PRIORITY_MEDIUM: str = "medium"
TASK_CATEGORY_BACKEND: str = "backend"

DOMAIN_MAPPING: Dict[str, str] = {
    "frontend": "technical",
    "backend": "technical",
    "database": "technical",
    "ai_ml": "technical",
    "devops": "technical",
    "qa": "technical",
    "security": "technical",
    "design": "non_technical",
    "product": "non_technical",
    "management": "non_technical",
    "product manager": "non_technical",
}

SLACK_BLOCK_TEXT_PLAIN: str = "plain_text"
SLACK_BLOCK_TEXT_MRKDWN: str = "mrkdwn"
SLACK_BLOCK_TYPE_HEADER: str = "header"
SLACK_BLOCK_TYPE_SECTION: str = "section"
SLACK_BLOCK_TYPE_DIVIDER: str = "divider"
SLACK_BLOCK_TYPE_CONTEXT: str = "context"

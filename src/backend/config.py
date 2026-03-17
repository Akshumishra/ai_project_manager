import os
from dotenv import load_dotenv

# Load .env file if it exists, otherwise use environment variables
try:
    load_dotenv(override=False)
except Exception:
    # If .env file doesn't exist or can't be read, continue with environment variables
    pass

class Config:
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    BOT_USER_ID = os.getenv("BOT_USER_ID")
    DATABASE_URL = os.getenv("DATABASE_URL")
    STANDUP_DATABASE_URL = os.getenv("STANDUP_DATABASE_URL")
    BASE_TASK_URL = os.getenv("BASE_TASK_URL", "https://ai-project-manager.com/tasks")

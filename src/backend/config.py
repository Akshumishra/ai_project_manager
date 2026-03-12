import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    BOT_USER_ID = os.getenv("BOT_USER_ID")

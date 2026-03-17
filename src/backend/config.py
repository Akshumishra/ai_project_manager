import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    # Database
    DATABASE_URL: str = Field(default=os.getenv("DATABASE_URL", ""))
    STANDUP_DATABASE_URL: Optional[str] = Field(default=os.getenv("STANDUP_DATABASE_URL"))

    # Slack
    SLACK_BOT_TOKEN: str = Field(default=os.getenv("SLACK_BOT_TOKEN", ""))
    SLACK_SIGNING_SECRET: str = Field(default=os.getenv("SLACK_SIGNING_SECRET", ""))
    BOT_USER_ID: str = Field(default=os.getenv("BOT_USER_ID", ""))
    SLACK_API_BASE_URL: str = Field(default="https://slack.com/api")

    # OpenAI
    OPENAI_API_KEY: str = Field(default=os.getenv("OPENAI_API_KEY", ""))

    # App Metadata
    APP_TITLE: str = Field(default="AI Project Manager Chatbot API")

    # Logging
    LOG_LEVEL: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    LOG_FORMAT: str = Field(default='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

settings = Settings()

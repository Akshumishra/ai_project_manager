<<<<<<< feat/qa_chatbot
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
=======
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    ALGORITHM: str
    ALLOWED_ORIGINS: list
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ACCESS_SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Email Config
    EMAILS_FROM: str | None = None
    RESEND_API_KEY: str | None = None
    BREVO_API_KEY: str | None = None
    SMTP_SERVER: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    FRONTEND_URL: str = "http://localhost:5173"
    OPENAI_API_KEY: str | None=None
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()
>>>>>>> dev

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_root = Path(__file__).resolve().parent
_project_root = _backend_root.parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str
    ALGORITHM: str
    ALLOWED_ORIGINS: list = []
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ACCESS_SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/ai_pm"
    ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: list = ["*"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ACCESS_SECRET_KEY: str = "your_access_secret_key"
    REFRESH_SECRET_KEY: str = "your_refresh_secret_key"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email settings
    EMAILS_FROM: str | None = None
    RESEND_API_KEY: str | None = None
    BREVO_API_KEY: str | None = None
    SMTP_SERVER: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    FRONTEND_URL: str = "http://localhost:5173"
    OPENAI_API_KEY: str | None = None

    # ── Meeting Bot Specific Configurations ──────────────────────────────────
    FIREFLIES_API_KEY: str | None = None
    APP_ENVIRONMENT: str = "development"

    GOOGLE_CREDENTIALS_PATH: Path = Field(
        default_factory=lambda: _project_root / "credentials.json"
    )
    GOOGLE_TOKEN_PATH: Path = Field(
        default_factory=lambda: _project_root / "token.json"
    )

    OPENAI_API_KEY: str | None=None
    SLACK_BOT_TOKEN: str | None = None
    SLACK_SIGNING_SECRET: str | None = None
    BOT_USER_ID: str | None = None
    SLACK_API_BASE_URL: str = "https://slack.com/api"
    APP_TITLE: str = "AI Project Manager API"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    model_config = SettingsConfigDict(
        env_file=(
            str(_backend_root / ".env"),
            str(_backend_root / "meeting_bot" / ".env"),
            ".env",
        ),
        extra="ignore",
    )

settings = Settings()
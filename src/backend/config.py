from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_root = Path(__file__).resolve().parent
_project_root = _backend_root.parent.parent


class Settings(BaseSettings):
    """
    Centralized configuration management with type validation and environment loading.
    """
    model_config = SettingsConfigDict(
        env_file=(
            str(_project_root / ".env"),
            str(_backend_root / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App Metadata ─────────────────────────────────────────────────────────
    APP_TITLE: str = "AI Project Manager API"
    APP_ENVIRONMENT: str = "development"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Auth ─────────────────────────────────────────────────────────────────
    ALGORITHM: str = "HS256"
    ACCESS_SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── AI / OpenAI ──────────────────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None

    # ── Email Config ─────────────────────────────────────────────────────────
    EMAILS_FROM: Optional[str] = None
    RESEND_API_KEY: Optional[str] = None
    BREVO_API_KEY: Optional[str] = None
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FRONTEND_URL: str = "http://localhost:5173"

    # ── Slack ────────────────────────────────────────────────────────────────
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_WORKSPACE_INVITE_URL: Optional[str] = None
    SLACK_WORKSPACE_NAME: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    BOT_USER_ID: Optional[str] = None
    SLACK_API_BASE_URL: str = "https://slack.com/api"

    # ── Misc / Optional integrations ─────────────────────────────────────────
    FIREFLIES_API_KEY: Optional[str] = None
    GOOGLE_CREDENTIALS_PATH: Path = Field(
        default_factory=lambda: _project_root / "credentials.json"
    )
    GOOGLE_TOKEN_PATH: Path = Field(
        default_factory=lambda: _project_root / "token.json"
    )

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @property
    def is_production(self) -> bool:
        """Return True when running in production mode."""
        return self.APP_ENVIRONMENT == "production"


settings = Settings()

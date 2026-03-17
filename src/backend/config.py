from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_root = Path(__file__).resolve().parent
_project_root = _backend_root.parent.parent


class Settings(BaseSettings):
    """
    Centralized configuration management with type validation and environment loading.
    """

    DATABASE_URL: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ACCESS_SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # ── Email Config ─────────────────────────────────────────────────────────
    EMAILS_FROM: str | None = None
    RESEND_API_KEY: str | None = None
    BREVO_API_KEY: str | None = None
    SMTP_SERVER: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    FRONTEND_URL: str = "http://localhost:5173"

    # ── AI / OpenAI ──────────────────────────────────────────────────────────
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

    model_config = SettingsConfigDict(
        env_file=(
            str(_backend_root / ".env"),
            str(_backend_root / "meeting_bot" / ".env"),
            ".env",
        ),
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        """Return True when running in production mode."""
        return self.APP_ENVIRONMENT == "production"


settings = Settings()
Config = settings

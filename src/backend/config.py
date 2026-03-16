"""
src.backend.config
~~~~~~~~~~~~~~~~~~

Centralized interface for loading all backend environment variables
using Pydantic BaseSettings.

Benefits:
- Automatic type coercion (e.g., str -> int/bool).
- Automatic .env loading with precedence rules.
- Validation bounds and structures for complex paths.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_root = Path(__file__).resolve().parent
_project_root = _backend_root.parent.parent


DEFAULT_MAX_DURATION = 4 * 60 * 60  # 4 hours


class AppConfig(BaseSettings):
    """
    Immutable structure containing ALL configuration vars with native Pydantic
    type casting and environment variable extraction.
    """

    # ── General Backend Configurations ───────────────────────────────────────
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # ── Meeting Bot Specific Configurations ──────────────────────────────────
    google_email: str = Field(alias="GOOGLE_EMAIL")

    # ── OAuth Credential Paths ───────────────────────────────────────────────
    google_credentials_path: Path = Field(
        default_factory=lambda: _project_root / "credentials.json",
        alias="GOOGLE_CREDENTIALS_PATH",
    )
    google_token_path: Path = Field(
        default_factory=lambda: _project_root / "token.json",
        alias="GOOGLE_TOKEN_PATH",
    )

    # ── Fireflies ────────────────────────────────────────────────────────────
    fireflies_api_key: str | None = Field(default=None, alias="FIREFLIES_API_KEY")

    # ── App Environment ──────────────────────────────────────────────────────
    environment: str = Field(default="development", alias="APP_ENVIRONMENT")

    # ── Configurations Dict for Environment mapping ──────────────────────────
    model_config = SettingsConfigDict(
        # Load from multiple env paths with priority triggers.
        # Inside the tuple, the files are loaded and merged.
        env_file=(
            str(_backend_root / ".env"),
            str(_backend_root / "meeting_bot" / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unmapped fields safely
    )

    @property
    def is_production(self) -> bool:
        """Return True when running in production mode."""
        return self.environment == "production"


# Backward Compatibility Alias for old Bot Config import chains
BotConfig = AppConfig

# Module-level singleton
_config: AppConfig | None = None


def get_app_config() -> AppConfig:
    """Return the global AppConfig singleton, initializing on first call."""
    global _config  # noqa: PLW0603
    if _config is None:
        # Pydantic BaseSettings automatically reads environment layout
        # during constructor instantiation.
        try:
            _config = AppConfig()
        except Exception as exc:
            # Re-raise friendly config error layout
            print(f"\n❌  Configuration Validation Error:\n{exc}\n")
            raise exc
    return _config


# Backward Compatibility Alias for Meeting Bot code
def get_config() -> AppConfig:
    """Alias for get_app_config() to prevent breaking old bot code imports."""
    return get_app_config()

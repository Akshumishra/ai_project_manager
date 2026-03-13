from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file).
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)


def _require_env(name: str) -> str:
    """Return the environment variable *name*, raising ValueError if absent."""
    value = os.getenv(name)
    if not value:
        raise ValueError(
            f"Required environment variable '{name}' is not set. "
            "Copy .env.example to .env and fill in the value."
        )
    return value


def _optional_env(name: str, default: str) -> str:
    """Return the environment variable *name*, falling back to *default*."""
    return os.getenv(name) or default


DEFAULT_MAX_DURATION = 4 * 60 * 60  # 4 hours


@dataclass(frozen=True)
class BotConfig:
    """Immutable configuration for a single bot process."""

    google_email: str
    google_password: str
    browser_profile_dir: Path
    recordings_dir: Path
    audio_device: str
    bot_display_name: str
    headless: bool
    max_concurrent_sessions: int
    max_duration: int

    def __post_init__(self) -> None:
        # Ensure directories exist at startup so we fail fast.
        object.__setattr__(self, "browser_profile_dir", Path(self.browser_profile_dir))
        object.__setattr__(self, "recordings_dir", Path(self.recordings_dir))
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Construct a BotConfig by reading the process environment."""
        default_profile = str(Path.home() / ".meet_bot_profile")
        return cls(
            google_email=_require_env("GOOGLE_EMAIL"),
            google_password=os.getenv("GOOGLE_PASSWORD", ""),
            browser_profile_dir=Path(
                _optional_env("BROWSER_PROFILE_DIR", default_profile)
            ),
            recordings_dir=Path(_optional_env("RECORDINGS_DIR", "./recordings")),
            audio_device=_optional_env("AUDIO_DEVICE", "BlackHole 2ch"),
            bot_display_name=_optional_env("BOT_DISPLAY_NAME", "Meeting Bot"),
            headless=_optional_env("HEADLESS", "true").lower() == "true",
            max_concurrent_sessions=int(_optional_env("MAX_CONCURRENT_SESSIONS", "1")),
            max_duration=int(_optional_env("MAX_DURATION", str(DEFAULT_MAX_DURATION))),
        )


# Module-level singleton — callers import this rather than constructing their own.
config: BotConfig | None = None


def get_config() -> BotConfig:
    """Return the module-level BotConfig singleton, creating it on first call."""
    global config  # noqa: PLW0603
    if config is None:
        config = BotConfig.from_env()
    return config

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from meeting_bot.bot.session_manager import SessionManager
from meeting_bot.config import BotConfig, get_config

logger = logging.getLogger(__name__)


class MultiSessionOrchestrator:
    """
    Spawns and manages a pool of concurrent SessionManager instances.
    """

    def __init__(self, config: BotConfig | None = None) -> None:
        self._config = config or get_config()
        # session_id -> {"task": Task, "manager": SessionManager, "url": str}
        self._active_sessions: dict[str, dict] = {}
        # Base directory for temporary per-session profiles.
        self._profiles_base = self._config.browser_profile_dir / "sessions"
        self._profiles_base.mkdir(parents=True, exist_ok=True)

    async def start_session(
        self,
        meet_url: str,
        audio_device: str | None = None,
        max_duration: int | None = None,
    ) -> str:
        """
        Start a new meeting session in a background task.

        Returns
        -------
        str
            A unique session ID.
        """
        session_id = str(uuid4())[:8]
        profile_dir = self._profiles_base / f"session_{session_id}"

        # ── Copy master profile to session profile to reuse login state ──
        if self._config.browser_profile_dir.exists():
            import shutil

            try:
                # Use shutil.copytree to duplicate the profile.
                shutil.copytree(
                    self._config.browser_profile_dir,
                    profile_dir,
                    ignore=shutil.ignore_patterns("sessions", "*.lock", "Singleton*"),
                    dirs_exist_ok=True,
                )
                logger.debug(
                    "Copied master profile to session profile: %s", profile_dir
                )
            except Exception as e:
                logger.warning("Could not copy profile: %s", e)

        # Use the provided audio device or fallback to config.
        device = audio_device or self._config.audio_device
        duration = max_duration or self._config.max_duration

        manager = SessionManager(
            config=self._config, user_data_dir=profile_dir, audio_device=device
        )

        task = asyncio.create_task(
            self._run_session(session_id, manager, meet_url, duration)
        )
        self._active_sessions[session_id] = {
            "task": task,
            "manager": manager,
            "url": meet_url,
        }

        logger.info("Started session %s for URL: %s", session_id, meet_url)
        return session_id

    async def _run_session(
        self, session_id: str, manager: SessionManager, url: str, duration: int
    ) -> None:
        """Internal wrapper to run the session and cleanup afterwards."""
        try:
            await manager.run(url, max_duration_seconds=duration)
        except asyncio.CancelledError:
            logger.info("Session %s was cancelled.", session_id)
        except Exception as exc:
            logger.error("Session %s failed: %s", session_id, exc)
        finally:
            self._active_sessions.pop(session_id, None)
            logger.info("Session %s finished and removed from pool.", session_id)

    async def stop_session(self, session_id: str) -> bool:
        """Stop a specific active session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return False

        logger.info("Requesting stop for session %s...", session_id)
        # We don't just cancel the task; we want the SessionManager to cleanup (teardown).
        # SessionManager.run() handles cleanup in 'finally'.
        # But we need a way to tell it to STOP wait_for_meeting_end.
        # Since SessionManager doesn't have an explicit 'stop' event yet,
        # we can cancel the task which triggers the 'finally' block.
        session["task"].cancel()
        return True

    def list_sessions(self) -> list[dict]:
        """Return a list of metadata for all active sessions."""
        return [
            {"id": sid, "url": data["url"]}
            for sid, data in self._active_sessions.items()
        ]

    async def wait_all(self) -> None:
        """Block until all active sessions have finished."""
        if not self._active_sessions:
            return

        logger.info(
            "Waiting for %d active sessions to finish...", len(self._active_sessions)
        )
        # Extract the tasks from our dict
        tasks = [data["task"] for data in self._active_sessions.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def active_count(self) -> int:
        return len(self._active_sessions)

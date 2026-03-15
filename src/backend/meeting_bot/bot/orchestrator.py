from __future__ import annotations

import asyncio
import logging
from uuid import UUID, uuid4

from meeting_bot.bot.session_manager import SessionManager
from meeting_bot.config import BotConfig, get_config

logger = logging.getLogger(__name__)


class MultiSessionOrchestrator:
    """
    Spawns and manages a pool of concurrent SessionManager instances.

    DB lifecycle hooks
    ------------------
    When ``db_enabled=True`` (which requires DATABASE_URL in the env), the
    orchestrator writes Meeting rows at these points:

    1. ``start_session()``  →  ``create_meeting()``   [status: SCHEDULED]
    2. After ``bot.join_meeting()`` succeeds  →  ``mark_meeting_started()``  [IN_PROGRESS]
    3. After the meeting ends (finally block)  →  ``mark_meeting_ended()``   [COMPLETED]
                                              →  ``create_transcript_record()``  [PENDING]
    4. ``stop_session()``   →  ``mark_meeting_cancelled()``  [CANCELLED]

    If DATABASE_URL is absent or the import fails, DB writes are silently
    skipped so the bot can still operate without a database connection.
    """

    def __init__(self, config: BotConfig | None = None) -> None:
        self._config = config or get_config()
        # session_id -> {"task": Task, "manager": SessionManager, "url": str}
        self._active_sessions: dict[str, dict] = {}
        self._profiles_base = self._config.browser_profile_dir / "sessions"
        self._profiles_base.mkdir(parents=True, exist_ok=True)
        self._db_enabled = self._check_db_available()

    # ── DB availability ────────────────────────────────────────────────────────

    @staticmethod
    def _check_db_available() -> bool:
        """Return True only if DATABASE_URL is set and imports succeed."""
        import os

        if not os.environ.get("DATABASE_URL"):
            logger.info(
                "DATABASE_URL not set — meeting DB persistence disabled. "
                "Add it to .env to enable."
            )
            return False
        try:
            import src.backend.db.meeting_service  # noqa: F401 — verify import works

            return True
        except Exception as exc:
            logger.warning("DB service unavailable, skipping persistence: %s", exc)
            return False

    # ── Public API ─────────────────────────────────────────────────────────────

    async def start_session(
        self,
        meet_url: str,
        audio_device: str | None = None,
        max_duration: int | None = None,
        *,
        # Optional DB metadata — only used when DATABASE_URL is configured.
        project_id: UUID | None = None,
        created_by: UUID | None = None,
        title: str | None = None,
        task_id: UUID | None = None,
        agenda: str | None = None,
    ) -> str:
        """
        Start a new meeting session in a background task.

        Returns
        -------
        str
            A unique session ID (8-char hex prefix of a UUID4).
        """
        session_id = str(uuid4())[:8]
        profile_dir = self._profiles_base / f"session_{session_id}"

        # ── Copy master profile so each session gets fresh cookies ──────────
        if self._config.browser_profile_dir.exists():
            import shutil

            try:
                shutil.copytree(
                    self._config.browser_profile_dir,
                    profile_dir,
                    ignore=shutil.ignore_patterns("sessions", "*.lock", "Singleton*"),
                    dirs_exist_ok=True,
                )
                logger.debug("Copied master profile to: %s", profile_dir)
            except Exception as exc:
                logger.warning("Could not copy browser profile: %s", exc)

        device = audio_device or self._config.audio_device
        duration = max_duration or self._config.max_duration

        manager = SessionManager(
            config=self._config, user_data_dir=profile_dir, audio_device=device
        )

        # ── Persist Meeting record immediately ───────────────────────────────
        if self._db_enabled and project_id and created_by:
            await asyncio.to_thread(
                self._db_create_meeting,
                session_id=session_id,
                meet_url=meet_url,
                project_id=project_id,
                created_by=created_by,
                title=title or meet_url,
                task_id=task_id,
                agenda=agenda,
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

    async def stop_session(self, session_id: str) -> bool:
        """Cancel a specific active session and mark it CANCELLED in the DB."""
        session = self._active_sessions.get(session_id)
        if not session:
            return False

        logger.info("Requesting stop for session %s...", session_id)

        if self._db_enabled:
            await asyncio.to_thread(self._db_cancel_meeting, session_id)

        session["task"].cancel()
        return True

    def list_sessions(self) -> list[dict]:
        """Return metadata for all active sessions."""
        return [
            {"id": sid, "url": data["url"]}
            for sid, data in self._active_sessions.items()
        ]

    async def wait_all(self) -> None:
        """Block until all active sessions have finished."""
        if not self._active_sessions:
            return
        logger.info(
            "Waiting for %d active session(s) to finish...", len(self._active_sessions)
        )
        tasks = [data["task"] for data in self._active_sessions.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def active_count(self) -> int:
        return len(self._active_sessions)

    # ── Internal session runner ────────────────────────────────────────────────

    async def _run_session(
        self, session_id: str, manager: SessionManager, url: str, duration: int
    ) -> None:
        """Run one session end-to-end, writing lifecycle events to the DB."""
        try:
            await manager.run(
                url,
                max_duration_seconds=duration,
                on_joined=self._make_on_joined_callback(session_id),
            )
        except asyncio.CancelledError:
            logger.info("Session %s was cancelled.", session_id)
        except Exception as exc:
            logger.error("Session %s failed: %s", session_id, exc, exc_info=True)
        finally:
            self._active_sessions.pop(session_id, None)
            logger.info("Session %s finished and removed from pool.", session_id)

            # Mark meeting as ended and create a transcript placeholder.
            if self._db_enabled:
                await asyncio.to_thread(self._db_end_meeting, session_id)

    def _make_on_joined_callback(self, session_id: str):
        """Return a coroutine callback that fires once the bot joins the meeting."""

        async def _on_joined() -> None:
            if self._db_enabled:
                await asyncio.to_thread(self._db_start_meeting, session_id)

        return _on_joined

    # ── DB write helpers (run in thread pool via asyncio.to_thread) ───────────

    @staticmethod
    def _db_create_meeting(
        *,
        session_id: str,
        meet_url: str,
        project_id: UUID,
        created_by: UUID,
        title: str,
        task_id: UUID | None,
        agenda: str | None,
    ) -> None:
        try:
            from src.backend.db.meeting_service import create_meeting

            create_meeting(
                project_id=project_id,
                created_by=created_by,
                title=title,
                meet_url=meet_url,
                bot_session_id=session_id,
                task_id=task_id,
                agenda=agenda,
            )
        except Exception as exc:
            logger.error("DB create_meeting failed for session %s: %s", session_id, exc)

    @staticmethod
    def _db_start_meeting(session_id: str) -> None:
        try:
            from src.backend.db.meeting_service import mark_meeting_started

            mark_meeting_started(session_id)
        except Exception as exc:
            logger.error(
                "DB mark_meeting_started failed for session %s: %s", session_id, exc
            )

    @staticmethod
    def _db_end_meeting(session_id: str) -> None:
        try:
            from src.backend.db.meeting_service import create_transcript_record, mark_meeting_ended

            mark_meeting_ended(session_id)
            create_transcript_record(session_id)  # Stub for transcription pipeline.
        except Exception as exc:
            logger.error(
                "DB mark_meeting_ended failed for session %s: %s", session_id, exc
            )

    @staticmethod
    def _db_cancel_meeting(session_id: str) -> None:
        try:
            from src.backend.db.meeting_service import mark_meeting_cancelled

            mark_meeting_cancelled(session_id)
        except Exception as exc:
            logger.error(
                "DB mark_meeting_cancelled failed for session %s: %s", session_id, exc
            )

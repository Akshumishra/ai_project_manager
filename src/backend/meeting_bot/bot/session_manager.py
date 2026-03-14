from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from meeting_bot.bot.audio_recorder import AudioRecorder
from meeting_bot.bot.meet_bot import MeetBot
from meeting_bot.config import BotConfig, get_config

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Coordinates the browser bot and audio recorder for one meeting session.

    Example::

        manager = SessionManager()
        recording = asyncio.run(manager.run("https://meet.google.com/abc-defg-hij"))
        print(f"Saved: {recording}")
    """

    def __init__(
        self,
        config: BotConfig | None = None,
        user_data_dir: Path | None = None,
        audio_device: str | None = None,
    ) -> None:
        self._config = config or get_config()
        self._bot = MeetBot(self._config, user_data_dir=user_data_dir)
        self._recorder = AudioRecorder(self._config, audio_device=audio_device)

    async def run(
        self,
        meet_url: str,
        max_duration_seconds: int | None = None,
    ) -> Path | None:
        """
        Execute a full meeting session end-to-end.

        Parameters
        ----------
        meet_url:
            The Google Meet URL (e.g. ``https://meet.google.com/xxx-yyy-zzz``).
        max_duration_seconds:
            Hard cap on recording time; the bot leaves after this many seconds
            even if the meeting is still active. Defaults to 4 hours.

        Returns
        -------
        Path | None
            Path to the recorded WAV file, or ``None`` if recording failed.
        """
        output_path: Path | None = None

        try:
            # ── 1. Start recording BEFORE joining so we capture everything. ──
            logger.info("Starting audio recorder…")
            output_path = await self._recorder.async_start()
            
            # Give ffmpeg a moment to initialize and check if it's still alive.
            # If it dies immediately (e.g. invalid device), we shouldn't continue.
            await asyncio.sleep(2.0)
            if not self._recorder.is_recording:
                logger.error("Audio recorder failed to stay alive. Check logs for ffmpeg errors.")
                raise RuntimeError("Audio recorder failed to start properly (invalid device or configuration).")

            logger.info("Recorder started successfully. Output path: %s", output_path)

            # ── 2. Set up browser and join meeting. ───────────────────────────
            await self._bot.setup()
            await self._bot.join_meeting(meet_url)

            # ── 3. Block until the meeting ends or timeout. ───────────────────
            duration = max_duration_seconds or self._config.max_duration
            await self._bot.wait_for_meeting_end(max_seconds=duration)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received — stopping session.")

        except Exception as exc:
            logger.exception("Unexpected error during meeting session: %s", exc)
            raise

        finally:
            # ── 4. Always stop recorder and leave meeting. ────────────────────
            logger.info("Finalising session…")

            stop_tasks = [
                self._recorder.async_stop(),
                self._leave_and_teardown(),
            ]
            results = await asyncio.gather(*stop_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error("Error during cleanup: %s", result)

        logger.info("Session complete. Recording: %s", output_path)
        return output_path

    async def seed_login(self) -> None:
        """
        Open a browser window for a one-time interactive Google login.

        Saves the session cookies to the persistent profile directory so
        subsequent ``run()`` calls skip the login step automatically.
        """
        await self._bot.setup(headless=False)
        try:
            await self._bot.seed_login()
        finally:
            await self._bot.teardown()

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _leave_and_teardown(self) -> None:
        """Leave the meeting and close the browser — safe to call at any time."""
        try:
            await self._bot.leave_meeting()
        except Exception as exc:
            logger.debug("leave_meeting() raised: %s", exc)
        finally:
            await self._bot.teardown()

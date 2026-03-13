from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from meeting_bot.config import BotConfig

logger = logging.getLogger(__name__)

# Output format: 16-bit PCM WAV, mono, 16 kHz — ideal for speech recognition later.
_SAMPLE_RATE = 16_000
_CHANNELS = 1
_FORMAT = "s16le"  # PCM signed 16-bit little-endian


def _build_ffmpeg_cmd(device: str, output_path: Path) -> list[str]:
    """
    Build the ffmpeg command for capturing macOS system audio.

    On macOS, ffmpeg reads from AVFoundation. The audio device index is
    resolved at runtime via :func:`_resolve_audio_device_index`.
    """
    return [
        "ffmpeg",
        "-y",  # Overwrite output without asking.
        "-f",
        "avfoundation",  # AVFoundation input (macOS).
        "-i",
        f":{device}",  # Audio-only device (colon prefix).
        "-ar",
        str(_SAMPLE_RATE),  # Sample rate.
        "-ac",
        str(_CHANNELS),  # Channels (mono).
        "-acodec",
        "pcm_s16le",  # WAV PCM codec.
        "-vn",  # No video stream.
        str(output_path),
    ]


def _output_filename(recordings_dir: Path) -> Path:
    """Return a timestamped WAV file path inside *recordings_dir*."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    recordings_dir.mkdir(parents=True, exist_ok=True)
    return recordings_dir / f"recording_{timestamp}.wav"


class AudioRecorder:
    """
    Wraps an ffmpeg subprocess to record virtual audio loopback to a WAV file.

    The recorder captures audio from the device named in ``config.audio_device``
    (defaults to ``BlackHole 2ch``). On macOS this device index may vary, so we
    resolve it via ``ffmpeg -list_devices`` before starting.
    """

    def __init__(self, config: BotConfig, audio_device: str | None = None) -> None:
        self._config = config
        self._audio_device = audio_device or config.audio_device
        self._process: subprocess.Popen[bytes] | None = None
        self._output_path: Path | None = None

    # ── Public interface ───────────────────────────────────────────────────────

    def start(self) -> Path:
        """
        Start the ffmpeg recording subprocess.

        Returns the :class:`~pathlib.Path` of the output WAV file being written.
        Raises :class:`RuntimeError` if already recording or if the audio
        device cannot be resolved.
        """
        if self._process is not None:
            raise RuntimeError("AudioRecorder is already running. Call stop() first.")

        device_id = self._resolve_audio_device_index(self._audio_device)
        self._output_path = _output_filename(self._config.recordings_dir)

        cmd = _build_ffmpeg_cmd(device_id, self._output_path)
        logger.info("Starting audio capture → %s", self._output_path)
        logger.debug("ffmpeg command: %s", " ".join(cmd))

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,  # Capture stderr to surface useful error messages.
        )
        logger.info("ffmpeg PID=%d recording started.", self._process.pid)
        return self._output_path

    def stop(self) -> Path | None:
        """
        Gracefully stop the ffmpeg subprocess by sending 'q\\n' to its stdin.

        Waits up to 10 seconds for a clean exit, then forcefully terminates.
        Returns the path of the completed recording file.
        """
        if self._process is None:
            logger.warning("stop() called but recorder was not running.")
            return self._output_path

        logger.info("Stopping audio capture (PID=%d)…", self._process.pid)

        try:
            if self._process.stdin:
                try:
                    # ffmpeg stops cleanly when it receives 'q' on stdin.
                    self._process.stdin.write(b"q\n")
                    self._process.stdin.flush()
                except (BrokenPipeError, OSError):
                    # Process might already be dead.
                    pass
        except Exception as exc:
            logger.debug("Error while sending stop signal to ffmpeg: %s", exc)

        try:
            self._process.wait(timeout=10)
            logger.info("ffmpeg exited (returncode=%d).", self._process.returncode)
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg did not exit in time — killing process.")
            self._process.kill()
            self._process.wait()

        # Log any critical ffmpeg errors.
        try:
            if self._process.stderr:
                stderr_tail = self._process.stderr.read().decode(errors="replace")[
                    -500:
                ]
                if stderr_tail:
                    logger.debug("ffmpeg stderr tail:\n%s", stderr_tail)
        except Exception:
            pass

        self._process = None
        logger.info("Recording session finalized.")
        return self._output_path

    @property
    def is_recording(self) -> bool:
        """True if ffmpeg is currently running."""
        return self._process is not None and self._process.poll() is None

    @property
    def output_path(self) -> Path | None:
        """Path of the current (or most recent) output file."""
        return self._output_path

    # ── Device resolution ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_audio_device_index(device_name: str) -> str:
        """
        Find the AVFoundation audio device index for *device_name*.

        Runs ``ffmpeg -f avfoundation -list_devices true -i ""`` and parses
        the stderr output. Falls back to the raw device name if parsing fails
        (ffmpeg accepts both indices and names for `-i`).
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Device list appears in stderr.
            output = result.stderr

            # Parse lines like: [AVFoundation indev @ ...] [3] BlackHole 2ch
            in_audio_section = False
            for line in output.splitlines():
                if "AVFoundation audio devices" in line:
                    in_audio_section = True
                    continue
                if in_audio_section and device_name.lower() in line.lower():
                    # Extract index in square brackets, e.g. [3]
                    import re

                    match = re.search(r"\[(\d+)\]", line)
                    if match:
                        idx = match.group(1)
                        logger.info(
                            "Resolved '%s' → device index %s.", device_name, idx
                        )
                        return idx
        except Exception as exc:
            logger.warning("Could not auto-resolve audio device index: %s", exc)

        # Default: pass the name directly (works on some ffmpeg builds).
        logger.info("Using raw device name as ffmpeg input: '%s'", device_name)
        return device_name

    # ── Async-compatible wrapper ───────────────────────────────────────────────

    async def async_start(self) -> Path:
        """Non-blocking wrapper around :meth:`start` for use in async code."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.start)

    async def async_stop(self) -> Path | None:
        """Non-blocking wrapper around :meth:`stop` for use in async code."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.stop)

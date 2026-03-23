from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from src.backend.config import settings
from src.backend.meeting_bot.constants import (
    FIREFLIES_API_BASE_URL,
    FIREFLIES_FETCH_TIMEOUT,
)
from src.backend.meeting_bot.services.meeting import (
    mark_meeting_ended,
    upsert_transcript,
)

logger = logging.getLogger(__name__)


class FirefliesClient:
    """Client for interacting with the Fireflies.ai GraphQL API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.FIREFLIES_API_KEY
        self.base_url = FIREFLIES_API_BASE_URL

    def _get_headers(self) -> dict[str, str]:
        """Build authenticated request headers."""
        if not self.api_key:
            raise ValueError(
                "FIREFLIES_API_KEY is not configured. "
                "Set it in your .env file or pass it to the constructor."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def fetch_transcript(self, transcript_id: str) -> dict:
        """
        Securely fetch a completed transcript from the Fireflies GraphQL API.
        """
        query = """
        query Transcript($id: String!) {
            transcript(id: $id) {
                id
                title
                date
                host_email
                video_url
                meeting_link
                meeting_attendees {
                    name
                    email
                }
                sentences {
                    index
                    start_time
                    end_time
                    text
                    speaker_name
                }
            }
        }
        """

        payload = {
            "query": query,
            "variables": {"id": str(transcript_id)},
        }

        try:
            async with httpx.AsyncClient(timeout=FIREFLIES_FETCH_TIMEOUT) as client:
                response = await client.post(
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                transcript = data.get("data", {}).get("transcript")
                if not transcript:
                    logger.warning("Empty transcript returned for %s", transcript_id)
                    return {"sentences": []}

                return transcript

        except httpx.HTTPStatusError as exc:
            err_msg = exc.response.text
            logger.error(
                "Failed to fetch Fireflies transcript %s: %s | Response: %s",
                transcript_id,
                exc,
                err_msg,
            )
            raise RuntimeError(
                f"Transcription fetch failed: HTTP {exc.response.status_code}"
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error("Fireflies transcript fetch timed out for %s", transcript_id)
            raise RuntimeError("Transcription fetch timed out") from exc
        except Exception as exc:
            logger.error(
                "Failed to fetch Fireflies transcript %s: %s", transcript_id, exc
            )
            raise RuntimeError("Transcription fetch failed") from exc


class FirefliesWebhookService:
    """Handles Fireflies transcript webhooks and orchestrates DB persistence."""

    def __init__(self):
        self._client = FirefliesClient()

    def _map_sentences(self, sentences: list[dict]) -> tuple[list[dict], str]:
        """Maps raw Fireflies sentence logic into internal format."""
        mapped_segments = [
            {
                "sequence": s.get("index", 0),
                "start_ms": int(float(s.get("start_time", 0)) * 1000)
                if s.get("start_time")
                else 0,
                "end_ms": int(float(s.get("end_time", 0)) * 1000)
                if s.get("end_time")
                else 0,
                "speaker_label": s.get("speaker_name", "Unknown"),
                "speaker_member_id": None,
                "text": s.get("text", ""),
            }
            for s in sentences
        ]

        raw_text_concat = "\n".join(
            f"{s.get('speaker_name', 'Unknown')}: {s.get('text', '')}"
            for s in sentences
        )
        return mapped_segments, raw_text_concat

    async def fetch_and_map_transcript(self, transcript_id: str) -> dict:
        """Fetches transcript details and maps them to internal schema."""
        try:
            raw_data = await self._client.fetch_transcript(transcript_id)
            sentences = raw_data.get("sentences", [])
            if not sentences:
                return {"status": "empty"}

            mapped_segments, raw_text = self._map_sentences(sentences)
            return {
                "status": "success",
                "raw_text": raw_text,
                "segments": mapped_segments,
                "meet_url": raw_data.get("meeting_link"),
                "attendees": raw_data.get("meeting_attendees", []),
            }
        except Exception:
            logger.exception("Failed to fetch transcript: %s", transcript_id)
            raise RuntimeError("Upstream Fireflies fetch failed")

    async def ingest_transcript(
        self, bot_session_id: Optional[str], transcript_data: dict
    ) -> str | None:
        """Persists transcript and marks meeting as ended."""
        try:
            resolved_id = await asyncio.to_thread(
                upsert_transcript,
                bot_session_id=bot_session_id,
                raw_text=transcript_data["raw_text"],
                segments=transcript_data["segments"],
                provider="fireflies",
                meet_url=transcript_data["meet_url"],
                meeting_attendees=transcript_data["attendees"],
            )

            if resolved_id:
                await asyncio.to_thread(mark_meeting_ended, resolved_id)

            return resolved_id
        except Exception:
            logger.exception("Transcript ingestion failed")
            raise RuntimeError("Database persistence failed")

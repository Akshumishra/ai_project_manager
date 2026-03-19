from __future__ import annotations

import logging

import httpx

from src.backend.config import settings
from src.backend.meeting_bot.constants import (
    FIREFLIES_API_BASE_URL,
    FIREFLIES_FETCH_TIMEOUT,
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

        This re-fetches from the API rather than trusting webhook payloads,
        preventing payload spoofing attacks.
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
                    logger.warning(
                        "Empty transcript returned for %s", transcript_id
                    )
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
            logger.error(
                "Fireflies transcript fetch timed out for %s", transcript_id
            )
            raise RuntimeError("Transcription fetch timed out") from exc
        except Exception as exc:
            logger.error(
                "Failed to fetch Fireflies transcript %s: %s", transcript_id, exc
            )
            raise RuntimeError("Transcription fetch failed") from exc

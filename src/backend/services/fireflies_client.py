from __future__ import annotations

import logging

import httpx

from src.backend.config import settings

logger = logging.getLogger(__name__)

# Default timeouts for Fireflies API calls
_SCHEDULE_TIMEOUT = 10.0
_FETCH_TIMEOUT = 30.0


class FirefliesClient:
    """Client for interacting with the Fireflies.ai GraphQL API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.FIREFLIES_API_KEY
        self.base_url = "https://api.fireflies.ai/graphql"

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

    async def schedule_bot(
        self, meeting_url: str, title: str, start_time: str
    ) -> dict:
        """
        Invite the Fireflies bot to a meeting using the addToLiveMeeting mutation.
        """
        if not self.api_key:
            logger.warning(
                "FIREFLIES_API_KEY is absent. Fireflies bot will not be invited."
            )
            return {"status": "skipped", "reason": "no_api_key"}

        payload = {
            "query": """
            mutation AddToLiveMeeting($meeting_link: String!) {
              addToLiveMeeting(meeting_link: $meeting_link) {
                success
              }
            }
            """,
            "variables": {"meeting_link": meeting_url},
        }

        try:
            async with httpx.AsyncClient(timeout=_SCHEDULE_TIMEOUT) as client:
                response = await client.post(
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                logger.info(
                    "Successfully scheduled Fireflies bot for %s", meeting_url
                )
                return {"status": "success", "data": response.json()}
        except httpx.HTTPStatusError as exc:
            err_msg = exc.response.text
            logger.error(
                "Failed to schedule Fireflies bot: %s | Response: %s", exc, err_msg
            )
            return {
                "status": "error",
                "reason": f"Client error: {exc.response.status_code}",
                "details": err_msg,
            }
        except httpx.TimeoutException:
            logger.error(
                "Fireflies bot scheduling timed out for %s", meeting_url
            )
            return {"status": "error", "reason": "timeout"}
        except Exception as exc:
            logger.error("Failed to schedule Fireflies bot: %s", exc)
            return {"status": "error", "reason": str(exc)}

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
            async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
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

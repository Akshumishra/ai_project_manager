from __future__ import annotations

import logging
import os
import stat
from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.backend.config import Config

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/meetings.space.settings",
]


def _get_credential_paths() -> tuple[Path, Path]:
    """Return resolved (token_path, credentials_path) from centralized config."""
    return Config.GOOGLE_TOKEN_PATH, Config.GOOGLE_CREDENTIALS_PATH


def _write_token_securely(token_path: Path, creds: Credentials) -> None:
    """
    Write OAuth token to disk with restrictive file permissions.

    The file is created with 0600 (owner read/write only) to prevent
    other users on the system from reading the credentials.
    """
    fd = os.open(
        str(token_path),
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        stat.S_IRUSR | stat.S_IWUSR,  # 0o600
    )
    try:
        os.write(fd, creds.to_json().encode())
    finally:
        os.close(fd)
    logger.info("OAuth token written securely to %s", token_path)


def _get_calendar_service():
    """
    Authenticate and return the Google Calendar API service client.

    Uses centralized config for file paths instead of hardcoded strings.
    """
    token_path, credentials_path = _get_credential_paths()
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                logger.warning("Token refresh failed: %s. Re-authenticating.", exc)
                creds = None
        else:
            creds = None

        if not creds:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Unable to find {credentials_path}. You must place your "
                    "Google OAuth Client secrets at the configured path."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        _write_token_securely(token_path, creds)

    return build("calendar", "v3", credentials=creds)


def create_calendar_meet(
    title: str,
    scheduled_at: datetime,
    duration_minutes: int = 45,
    invite_fireflies: bool = True,
) -> tuple[str | None, dict]:
    """
    Create a Google Calendar Event and auto-generate a Google Meet space.

    Returns ``(meet_url, event_dict)`` where ``meet_url`` may be None if
    the Meet link generation fails.
    """
    service = _get_calendar_service()

    end_time = scheduled_at + timedelta(minutes=duration_minutes)

    # ISO 8601 strings expected by Google APIs
    start_str = (
        scheduled_at.isoformat()
        if scheduled_at.tzinfo
        else scheduled_at.isoformat() + "Z"
    )
    end_str = (
        end_time.isoformat() if end_time.tzinfo else end_time.isoformat() + "Z"
    )

    event_body: dict = {
        "summary": title,
        "description": "AI Project Manager Scheduled Meeting",
        "start": {"dateTime": start_str, "timeZone": "UTC"},
        "end": {"dateTime": end_str, "timeZone": "UTC"},
        "conferenceData": {
            "createRequest": {
                "requestId": f"meet-{int(datetime.now().timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    if invite_fireflies:
        event_body["attendees"] = [{"email": "fred@fireflies.ai"}]
        logger.info(
            "Automatically adding fred@fireflies.ai to avoid Google Meet admit prompts."
        )

    logger.info("Pushing Google Calendar event creation for '%s'...", title)

    event = (
        service.events()
        .insert(calendarId="primary", body=event_body, conferenceDataVersion=1)
        .execute()
    )

    meet_url = None
    conference_data = event.get("conferenceData", {})
    entry_points = conference_data.get("entryPoints", [])

    for entry in entry_points:
        if entry.get("entryPointType") == "video":
            meet_url = entry.get("uri")
            break

    if not meet_url:
        logger.warning(
            "Event created but Meet URL was not generated. "
            "Verify app config scopes or domain delegation formats."
        )
    else:
        _unlock_meet_room_to_open(meet_url)

    return meet_url, event


def _get_meet_service():
    """Build the Google Meet API service v2 client."""
    token_path, _ = _get_credential_paths()

    if not token_path.exists():
        raise FileNotFoundError(
            "Missing token file for Meet Spaces setup. "
            "Run the OAuth flow first via the Calendar service."
        )

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    return build("meet", "v2", credentials=creds)


def _unlock_meet_room_to_open(meet_url: str) -> dict | None:
    """
    Update the Meet Space settings to accessType='OPEN' programmatically.

    This allows external guests to bypass the admission wall.
    """
    if not meet_url:
        return None

    meet_code = meet_url.split("/")[-1]

    try:
        meet_service = _get_meet_service()
        space_alias = f"spaces/{meet_code}"

        logger.info("Resolving true space name for alias %s...", space_alias)
        space = meet_service.spaces().get(name=space_alias).execute()
        true_name = space.get("name")

        logger.info("Patching space %s accessType to OPEN...", true_name)
        body = {"config": {"accessType": "OPEN"}}
        updated_space = (
            meet_service.spaces()
            .patch(name=true_name, body=body, updateMask="config.accessType")
            .execute()
        )

        logger.info(
            "Successfully unlocked meeting space room '%s' to OPEN access.",
            true_name,
        )
        return updated_space

    except Exception as exc:
        logger.warning(
            "Failed to unlock meet room to OPEN: %s. Verify Google Meet API is "
            "enabled on Cloud Console and you've authorized the new scopes.",
            exc,
        )
        return None

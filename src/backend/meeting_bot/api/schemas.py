from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ScheduleCalendarMeetingRequest(BaseModel):
    """Request schema for scheduling a Google Calendar meeting."""

    project_id: UUID
    created_by: UUID
    agenda: str
    title: str = Field(default="Scheduled Meeting")
    task_id: UUID | None = None
    scheduled_at: str = Field(description="ISO-8601 formatted datetime string with timezone.")
    duration_minutes: int = Field(
        default=45,
        ge=5,
        le=480,
        description="Duration in minutes (5–480). Default 45.",
    )


class ScheduleCalendarMeetingResponse(BaseModel):
    """Response schema for a successfully scheduled meeting."""

    meeting_id: UUID
    meet_url: str
    message: str
    inferred_participants: list[dict]


class FirefliesWebhookPayload(BaseModel):
    """Inbound webhook payload from Fireflies.ai transcript completion."""

    transcript_id: str | None = Field(default=None, alias="transcriptId")
    meeting_id: str | None = Field(default=None, alias="meetingId")
    bot_session_id: str | None = Field(
        default=None,
        description="Internal ID if forwarded through a middleware.",
    )

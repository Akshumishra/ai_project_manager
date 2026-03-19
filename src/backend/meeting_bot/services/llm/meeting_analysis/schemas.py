from __future__ import annotations

from pydantic import BaseModel, Field


class Decision(BaseModel):
    """A binding decision made during the meeting."""

    description: str = Field(description="The narrative of the decision made.")
    decided_by_name: str | None = Field(
        None,
        description="Name of the person who made or approved the decision.",
    )
    timestamp_ms: int | None = Field(
        None,
        description="Approximate millisecond timestamp offset if known, else null.",
    )


class RiskBlocker(BaseModel):
    """A risk or blocker identified during the meeting."""

    description: str = Field(description="Narrative of the blocker or risk.")
    severity: str = Field(
        description="Must be one of: 'low', 'medium', 'high'.",
    )


class ExtractedActionItem(BaseModel):
    """An actionable task extracted from meeting discussion."""

    description: str = Field(
        description="Action item narrative of what needs doing.",
    )
    source_quote: str | None = Field(
        None,
        description="Verbatim transcript quote where this item was identified.",
    )
    due_date: str | None = Field(
        None,
        description="Due date if explicitly mentioned, ISO-8601 string or None.",
    )


class MeetingAnalysis(BaseModel):
    """Container for the full analysis structure extracted from LLM."""

    summary_text: str = Field(
        description="A cohesive narrative summary covering the high-level meeting topics and outcome.",
    )
    key_decisions: list[Decision] = Field(
        default_factory=list,
        description="Structured list of all binding decisions.",
    )
    risks_and_blockers: list[RiskBlocker] = Field(
        default_factory=list,
        description="Structured list of blockers & risks.",
    )
    action_items: list[ExtractedActionItem] = Field(
        default_factory=list,
        description="Actionable tasks extracted from discussion.",
    )



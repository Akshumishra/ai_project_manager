from __future__ import annotations

import asyncio
import logging
from typing import Optional, List

from langchain_openai import ChatOpenAI
from sqlalchemy import text

from src.backend.config import settings
from src.backend.meeting_bot.constants import DEFAULT_AI_MODEL, DEFAULT_AI_TEMPERATURE
from src.backend.meeting_bot.services.meeting.analysis import (
    add_action_items,
    save_summary,
)
from src.backend.meeting_bot.services.meeting.session import get_db_session
from src.backend.meeting_bot.services.slack_notification import (
    post_task_mapping_notification,
)

from .prompts import TRANSCRIPT_PROMPT
from .schemas import MeetingAnalysis

logger = logging.getLogger(__name__)


class MeetingAnalysisService:
    """Orchestrates the AI-driven transcript processing pipeline."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.llm = (
            ChatOpenAI(
                model=DEFAULT_AI_MODEL,
                temperature=DEFAULT_AI_TEMPERATURE,
                api_key=self.api_key,
            )
            if self.api_key
            else None
        )

    def _build_agent_context(
        self, db, bot_session_id: str, analysis: MeetingAnalysis
    ) -> dict | None:
        """Fetches meeting details to build context for the next pipeline step."""
        meet = db.execute(
            text(
                "SELECT id, project_id, title FROM meetings WHERE bot_session_id = :sid"
            ),
            {"sid": bot_session_id},
        ).fetchone()
        if not meet:
            return None

        meet_id, project_id, title = meet

        participants_res = db.execute(
            text("""
                SELECT u.id, u.name, u.email 
                FROM meeting_participants mp 
                JOIN project_members pm ON mp.project_member_id = pm.id 
                JOIN users u ON pm.user_id = u.id 
                WHERE mp.meeting_id = :mid
            """),
            {"mid": meet_id},
        )
        participants = [
            {"id": str(r[0]), "name": r[1], "email": r[2]} for r in participants_res
        ]

        transcript_res = db.execute(
            text("SELECT segments FROM meeting_transcripts WHERE meeting_id = :mid"),
            {"mid": meet_id},
        ).fetchone()
        segments = transcript_res[0] if transcript_res else []

        attendee_map = {p["name"]: p["id"] for p in participants}

        return {
            "project_id": str(project_id),
            "meeting_title": title,
            "meeting_summary": analysis.summary_text,
            "meeting_participants": participants,
            "meeting_segments": segments,
            "attendee_mapping": attendee_map,
            "risks": [
                {
                    "description": r.description,
                    "likelihood": "medium",
                    "impact": r.severity,
                }
                for r in (analysis.risks_and_blockers or [])
            ],
            "action_items": [
                {
                    "description": a.description,
                    "assignee_tag": getattr(a, "assigned_to_email", "") or "",
                }
                for a in (analysis.action_items or [])
            ],
            "blockers": [],
        }

    def _trigger_task_mapping(self, bot_session_id: str, analysis: MeetingAnalysis):
        """Asynchronously trigger the Task Mapper Agent."""
        try:
            with get_db_session() as db:
                context = self._build_agent_context(db, bot_session_id, analysis)
                if not context:
                    return

                logger.info("Triggering Agent for session %s", bot_session_id)
                from src.backend.meeting_bot.services.llm.task_mapper_agent import (
                    run_task_mapping_agent,
                )

                mapping_res = run_task_mapping_agent(context)

                try:
                    asyncio.run(
                        post_task_mapping_notification(
                            context["project_id"], mapping_res
                        )
                    )
                except Exception as e:
                    logger.warning("Notification failed: %s", e)

        except Exception as e:
            logger.warning("Pipeline trigger failed for %s: %s", bot_session_id, e)

    def process_transcript(self, bot_session_id: str, transcript_text: str) -> bool:
        """Runs the complete analysis and post-processing pipeline."""
        if not self.llm or not transcript_text.strip():
            logger.warning(
                "Analysis skipped for session %s (Missing Key/Transcript)",
                bot_session_id,
            )
            return False

        try:
            logger.info("Analyzing transcript for session %s", bot_session_id)
            structured_llm = self.llm.with_structured_output(MeetingAnalysis)
            chain = TRANSCRIPT_PROMPT | structured_llm
            analysis: MeetingAnalysis = chain.invoke({"transcript": transcript_text})

            # 1. Save results to Database
            save_summary(
                bot_session_id=bot_session_id,
                summary_text=analysis.summary_text,
                key_decisions=[d.model_dump() for d in analysis.key_decisions],
                risks_and_blockers=[
                    r.model_dump() for r in analysis.risks_and_blockers
                ],
                ai_model=DEFAULT_AI_MODEL,
            )

            if analysis.action_items:
                add_action_items(
                    bot_session_id=bot_session_id,
                    items=[item.model_dump() for item in analysis.action_items],
                )

            # 2. Hand off to autonomous agent
            self._trigger_task_mapping(bot_session_id, analysis)

            return True
        except Exception:
            logger.exception("AI analysis failed for session %s", bot_session_id)
            return False


# Functional wrapper for legacy calls
def process_meeting_transcript(bot_session_id: str, transcript_text: str) -> bool:
    service = MeetingAnalysisService()
    return service.process_transcript(bot_session_id, transcript_text)

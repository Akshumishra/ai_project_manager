from __future__ import annotations

import json
import logging
import asyncio

from langchain_openai import ChatOpenAI

from src.backend.config import settings
from .prompts import TRANSCRIPT_PROMPT
from .schemas import MeetingAnalysis
from src.backend.services.meeting.analysis import add_action_items, save_summary
from sqlalchemy import text
from src.backend.services.meeting.session import get_db_session
from src.backend.services.slack_notification import post_task_mapping_notification
# from src.backend.services.llm.task_mapper_agent import run_task_mapping_agent # Removed due to circular import

logger = logging.getLogger(__name__)




def _trigger_task_mapper_pipeline(bot_session_id: str, summary_text: str, risks_list: list, actions_list: list):
    """Refactored helper to gather meeting context and run Task Mapper Agent."""
    try:
        with get_db_session() as db_session:
            meet_row = db_session.execute(
                text("SELECT id, project_id, title FROM meetings WHERE bot_session_id = :sid"),
                {"sid": bot_session_id}
            ).fetchone()
            
            if not meet_row:
                return
                
            meet_id, project_id, title = meet_row
            
            # Fetch participants
            participants_result = db_session.execute(text("""
                SELECT u.id, u.name, u.email 
                FROM meeting_participants mp 
                JOIN project_members pm ON mp.project_member_id = pm.id 
                JOIN users u ON pm.user_id = u.id 
                WHERE mp.meeting_id = :mid
            """), {"mid": meet_id})
            participants = [{"id": str(r[0]), "name": r[1], "email": r[2]} for r in participants_result]
            
            transcript_data = db_session.execute(text("SELECT segments FROM meeting_transcripts WHERE meeting_id = :mid"), {"mid": meet_id}).fetchone()
            segments = transcript_data[0] if transcript_data else []

            attendee_map = {p["name"]: p["id"] for p in participants}

            # Build Context for Agent
            map_context = {
                "project_id": str(project_id),
                "meeting_title": title,
                "meeting_summary": summary_text,
                "meeting_participants": participants,
                "meeting_segments": segments,
                "attendee_mapping": attendee_map,
                "blockers": [],
                "risks": [
                    {"description": r.description, "likelihood": "medium", "impact": r.severity}
                    for r in (risks_list or [])
                ],
                "action_items": [
                    {"description": a.description, "assignee_tag": getattr(a, 'assigned_to_email', '') or ""}
                    for a in (actions_list or [])
                ]
            }
            
            logger.info("Triggering Task Mapper Agent for session %s", bot_session_id)
            from src.backend.services.llm.task_mapper_agent import run_task_mapping_agent
            response_json = run_task_mapping_agent(map_context)
            logger.info("Task Mapper Agent completed successfully for session %s", bot_session_id)

            # ── 6. Dispatch Slack Notification ────────────────────────────────
            try:
                asyncio.run(post_task_mapping_notification(str(project_id), response_json))
            except Exception as slack_err:
                logger.warning("Non-blocking Slack notification failed for session %s: %s", bot_session_id, slack_err)


    except Exception as e:
         logger.warning("Optional Task Mapper Agent execution failed for session %s: %s", bot_session_id, e)


def process_meeting_transcript(bot_session_id: str, transcript_text: str) -> bool:
    """
    Process raw transcript through the automated AI analysis pipeline.
    Returns True on success, False if skipped or failed.
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.warning("AI processor skipped for session %s: OPENAI_API_KEY is not set.", bot_session_id)
        return False

    if not transcript_text or not transcript_text.strip():
        logger.info("AI processor skipped for session %s: transcript empty.", bot_session_id)
        return False

    try:
        logger.info("Starting automated AI analysis for session %s", bot_session_id)

        # 1. Initialize LangChain wrapper with structured output boundary
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=api_key)
        structured_llm = llm.with_structured_output(MeetingAnalysis)

        # 2. Synchronous model execution
        chain = TRANSCRIPT_PROMPT | structured_llm
        analysis: MeetingAnalysis = chain.invoke({"transcript": transcript_text})

        # 3. Auto-save narrative and decisions to MeetingSummary
        save_summary(
            bot_session_id=bot_session_id,
            summary_text=analysis.summary_text,
            key_decisions=[d.model_dump() for d in analysis.key_decisions],
            risks_and_blockers=[r.model_dump() for r in analysis.risks_and_blockers],
            ai_model="gpt-4o",
        )

        # 4. Bulk insert action items
        if analysis.action_items:
            add_action_items(
                bot_session_id=bot_session_id,
                items=[item.model_dump() for item in analysis.action_items],
            )

        # 5. Trigger Task Mapper & Slack Pipeline (decoupled)
        _trigger_task_mapper_pipeline(
            bot_session_id=bot_session_id,
            summary_text=analysis.summary_text,
            risks_list=analysis.risks_and_blockers,
            actions_list=analysis.action_items
        )

        logger.info("Automated AI analysis completed and saved for session %s", bot_session_id)
        return True

    except Exception:
        logger.exception(
            "Automated AI analysis failed for session %s", bot_session_id
        )
        return False


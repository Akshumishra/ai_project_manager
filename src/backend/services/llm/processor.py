"""
src.backend.services.ai.processor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

AI-powered processing pipeline for meeting transcripts and participant inference.

Uses LangChain with structured output to ensure type-safe, schema-validated
responses from GPT-4o.
"""

from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI

from src.backend.config import get_app_config
from src.backend.model.project import ProjectMember
from src.backend.model.user_detail import UserDetail
from src.backend.services.ai.prompts import PARTICIPANT_INFERENCE_PROMPT, TRANSCRIPT_PROMPT
from src.backend.services.ai.schemas import MeetingAnalysis, ParticipantInference
from src.backend.services.meeting.analysis import add_action_items, save_summary
from src.backend.services.meeting.session import get_db_session

logger = logging.getLogger(__name__)


def process_meeting_transcript(bot_session_id: str, transcript_text: str) -> bool:
    """
    Process raw transcript through the automated AI analysis pipeline.

    Returns True on success, False if skipped or failed.
    """
    api_key = get_app_config().openai_api_key
    if not api_key:
        logger.warning(
            "AI processor skipped for session %s: OPENAI_API_KEY is not set.",
            bot_session_id,
        )
        return False

    if not transcript_text or not transcript_text.strip():
        logger.info(
            "AI processor skipped for session %s: transcript empty.", bot_session_id
        )
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

        logger.info(
            "Automated AI analysis completed and saved for session %s",
            bot_session_id,
        )
        return True

    except Exception:
        logger.exception(
            "Automated AI analysis failed for session %s", bot_session_id
        )
        return False


def infer_meeting_participants(project_id: str, agenda: str) -> list[dict]:
    """
    AI agent that evaluates an agenda and project members to determine
    who should be invited to a scheduled meeting.

    Uses a context-managed DB session to prevent connection leaks.
    """
    api_key = get_app_config().openai_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    # 1. Gather project member context using a properly managed session
    members_data: list[dict] = []

    with get_db_session() as db:
        members = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id)
            .all()
        )
        for m in members:
            detail = (
                db.query(UserDetail)
                .filter(UserDetail.user_id == m.user_id)
                .first()
            )
            members_data.append(
                {
                    "project_member_id": str(m.id),
                    "user_id": str(m.user_id),
                    "skills": detail.skills if detail else "Unknown",
                    "designation": detail.designation if detail else "Unknown",
                    "experience": detail.experience if detail else "Unknown",
                }
            )

    # If no members, nothing to infer
    if not members_data:
        logger.warning("No active members in project %s to invite.", project_id)
        return []

    logger.info("Starting AI participant inference for project %s", project_id)

    # 2. Invoke the Strict Evaluator Agent
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=api_key)
    structured_llm = llm.with_structured_output(ParticipantInference)
    chain = PARTICIPANT_INFERENCE_PROMPT | structured_llm

    analysis: ParticipantInference = chain.invoke(
        {"agenda": agenda, "members_json": json.dumps(members_data)}
    )

    # 3. Return strictly sanitized output
    return [p.model_dump() for p in analysis.recommended_participants]

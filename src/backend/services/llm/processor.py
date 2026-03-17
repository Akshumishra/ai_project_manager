from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI

from src.backend.config import Config
from src.backend.services.llm.prompts import TRANSCRIPT_PROMPT
from src.backend.services.llm.schemas import MeetingAnalysis
from src.backend.services.meeting.analysis import add_action_items, save_summary

logger = logging.getLogger(__name__)


def process_meeting_transcript(bot_session_id: str, transcript_text: str) -> bool:
    """
    Process raw transcript through the automated AI analysis pipeline.

    Returns True on success, False if skipped or failed.
    """
    api_key = Config.OPENAI_API_KEY
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


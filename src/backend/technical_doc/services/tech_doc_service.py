import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.backend.technical_doc.tech_doc_agent.agent import TechDocAgent

from src.backend.model.document import DocumentType
from src.backend.model.tech_doc_chat import TechDocChat
from src.backend.utils.agent_chat_utils import get_agent_chat_history, save_agent_chat_message
from src.backend.utils.doc_utils import get_document_content
from src.backend.utils.get_project_details import get_project_detail
from src.backend.utils.workflow_utils import (
    set_workflow_status,
    check_agent_prerequisites,
    handle_agent_resumption,
)
from src.backend.technical_doc.constants import TechDocAgentConstants

logger = logging.getLogger(__name__)
AgentConst = TechDocAgentConstants

def get_chat_history(db: Session, project_id: UUID) -> List[Dict[str, str]]:
    return get_agent_chat_history(db, TechDocChat, project_id)


def save_chat_message(db: Session, project_id: UUID, role: str, content: str, user_id: UUID = None):
    save_agent_chat_message(db, TechDocChat, project_id, role, content, user_id)


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_prompt(db: Session, project_id: UUID) -> str:
    """Build the system-level context message sent at the start of every conversation."""
    project = get_project_detail(db, project_id) or {}
    title = project.get("name", "Untitled Project")
    req = get_document_content(db, project_id, DocumentType.REQUIREMENT) or "No Requirement Specification found."

    return (
        f"Project Title: {title}\n\n"
        f"Requirements:\n{req}\n\n"
        "Generate the technical specification and greet the user."
    )


def _build_messages(
    base_prompt: str,
    history: List[Dict[str, str]],
    current_doc: Optional[str] = None,
    user_message: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Assemble the message list passed to the LLM."""
    messages = [{"role": "user", "content": base_prompt}]

    if history:
        messages.extend(history)

    if current_doc and current_doc.strip():
        messages.append({"role": "user", "content": f"Current technical document:\n\n{current_doc}"})

    if user_message:
        messages.append({"role": "user", "content": user_message})

    return messages


# ── Agent execution ────────────────────────────────────────────────────────────

def _execute_agent(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    messages: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Run one agent turn.
    NOTE: The agent's `save_technical_specification` tool already persists the
    document to the database. No manual save is needed here.
    """

    set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "thinking")
    try:
        agent = TechDocAgent(user_id, project_id)
        response = agent.run(messages)

        if response.get("content"):
            save_chat_message(db, project_id, "assistant", response["content"])

        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "in_progress")
        return response

    except Exception as e:
        logger.exception(f"Agent error for project {project_id}: {e}")
        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "in_progress")
        raise HTTPException(status_code=502, detail=str(e))


# ── Main entry point ───────────────────────────────────────────────────────────

def run_tech_doc_agent(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    user_message: Optional[str] = None,
    is_start: bool = False,
) -> Dict[str, Any]:
    """
    Single entry point for the Tech Doc agent.
    Called by both GET (start/resume) and POST (new user message) routes.
    """
    # 1. Ensure prerequisites are met (e.g. requirement phase completed)
    redirect = check_agent_prerequisites(
        db, project_id, AgentConst.WORKFLOW_NAME,
        prereq_workflow=AgentConst.REQ_WORKFLOW_NAME,
        redirect_path=AgentConst.REDIRECT_PATH,
    )
    if redirect:
        return redirect

    history = get_chat_history(db, project_id)

    # 2. If agent is already thinking or session can be resumed, short-circuit
    resumption = handle_agent_resumption(db, project_id, AgentConst.WORKFLOW_NAME, history, is_start=is_start)
    if resumption:
        if not resumption.get("thinking"):
            resumption["document"] = get_document_content(db, project_id, DocumentType.TECHNICAL)
        return resumption

    # 3. Persist the user's message before sending it to the agent
    if user_message:
        save_chat_message(db, project_id, "user", user_message, user_id)

    # 4. Build context and run
    current_doc = get_document_content(db, project_id, DocumentType.TECHNICAL)
    base_prompt = _build_prompt(db, project_id)
    messages = _build_messages(base_prompt, history, current_doc, user_message)

    response = _execute_agent(db, user_id, project_id, messages)
    response["status"] = "started" if is_start else "running"
    return response
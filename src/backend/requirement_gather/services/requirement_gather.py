import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID

from src.backend.requirement_gather.requirement_agent.agent import RequirementAgent
from src.backend.requirement_gather.services.chat_history import (
    get_chat_history,
    save_chat_message,
    build_initial_user_prompt,
)
from src.backend.utils.workflow_utils import (
    set_workflow_status,
    check_agent_prerequisites,
    handle_agent_resumption,
    get_workflow_status,
)
from src.backend.utils.doc_utils import get_document_content
from src.backend.model.document import DocumentType
from src.backend.requirement_gather.constants import RequirementAgentConstants

logger = logging.getLogger(__name__)
AgentConst = RequirementAgentConstants


def _run_agent(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    messages: List[Dict[str, str]],
    is_recovering: bool = False,
) -> Dict[str, Any]:
    """
    Execute one agent turn, persist the assistant reply, and return the response.

    Args:
        is_recovering: True when resuming after an interrupted turn (last message was user).
                       Changes the returned status to "resumed" and attaches full history.
    """
    set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "thinking")
    agent = RequirementAgent(user_id, project_id)

    try:
        response = agent.run(messages)
        content = response.get("content")

        if not content:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Agent returned empty response")

        save_chat_message(db=db, project_id=project_id, role="assistant", content=content)
        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "in_progress")

        if is_recovering:
            return {
                "messages": get_chat_history(db, project_id),
                "status": "resumed",
                "saved": response.get("saved", False),
                "document": response.get("doc"),
            }

        if "doc" in response:
            response["document"] = response.pop("doc")

        wf = get_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME)
        if wf:
            response["status"] = wf.status

        return response

    except Exception as e:
        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "in_progress")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Agent failed: {str(e)}")


def start_requirement_agent(db: Session, user_id: UUID, project_id: UUID) -> Dict[str, Any]:
    """Start or resume the requirement gathering session."""
    redirect = check_agent_prerequisites(db, project_id, AgentConst.WORKFLOW_NAME, redirect_path=AgentConst.REDIRECT_PATH)
    if redirect:
        return redirect

    history = get_chat_history(db, project_id)
    resumption = handle_agent_resumption(db, project_id, AgentConst.WORKFLOW_NAME, history, is_start=True)

    if resumption:
        if not resumption.get("thinking"):
            resumption["document"] = get_document_content(db, project_id, DocumentType.REQUIREMENT)
        return resumption

    is_recovering = bool(history and history[-1]["role"] == "user")
    context = build_initial_user_prompt(db, project_id, user_id=user_id)
    messages = [{"role": "user", "content": context}, *history]

    result = _run_agent(db, user_id, project_id, messages, is_recovering=is_recovering)
    if not is_recovering:
        result["status"] = "started"
    return result


def run_requirement_agent(db: Session, user_id: UUID, project_id: UUID, user_message: str) -> Dict[str, Any]:
    """Process a new user message in the requirement gathering session."""
    save_chat_message(db=db, project_id=project_id, role="user", content=user_message, user_id=user_id)

    history = get_chat_history(db, project_id)
    context = build_initial_user_prompt(db, project_id, user_id=user_id)
    messages = [{"role": "user", "content": context}, *history]

    return _run_agent(db, user_id, project_id, messages)

def complete_requirement_step(db: Session, project_id: UUID) -> Dict[str, Any]:
    """
    Updates the workflow status to completed for the requirement step.
    """
    try:
        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "completed")
        db.commit()
        return {"status": "success", "message": "Requirement step marked as completed."}
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to complete requirement step for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete requirement step: {str(e)}"
        )

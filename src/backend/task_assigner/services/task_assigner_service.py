import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.backend.model.task_assigner_chat import TaskAssignerChat
from src.backend.utils.agent_chat_utils import get_agent_chat_history, save_agent_chat_message
from src.backend.utils.workflow_utils import (
    get_workflow_status,
    set_workflow_status,
    check_agent_prerequisites,
    handle_agent_resumption,
)
from src.backend.task_assigner.constants import TaskAssignerConstants
from src.backend.task_assigner.task_assigner_agent.agent import TaskAssignerAgent

logger = logging.getLogger(__name__)
AgentConst = TaskAssignerConstants


def get_chat_history(db: Session, project_id: UUID) -> List[Dict[str, str]]:
    return get_agent_chat_history(db, TaskAssignerChat, project_id)


def save_chat_message(db: Session, project_id: UUID, role: str, content: str, user_id: UUID = None):
    save_agent_chat_message(db, TaskAssignerChat, project_id, role, content, user_id)


# ── Agent execution ─────────────────────────────────────────────────────────────

def _execute_agent(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    messages: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Run one agent turn, persist the response, and return it."""
    set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "thinking")
    agent = TaskAssignerAgent(project_id)

    try:
        response = agent.run(messages)
        content = response.get("content")

        if content:
            save_chat_message(db, project_id, "assistant", content)

        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "in_progress")
        return response

    except Exception as e:
        db.rollback()
        logger.exception(f"Agent execution failed for project {project_id}: {e}")
        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "in_progress")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Agent failed: {str(e)}")


def run_task_assigner_agent(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    user_message: Optional[str] = None,
    is_start: bool = False,
) -> Dict[str, Any]:
    """Single entry point for the Task Assigner agent (start + message turns)."""
    redirect = check_agent_prerequisites(
        db, project_id, AgentConst.WORKFLOW_NAME,
        prereq_workflow="task_creation",
        redirect_path=AgentConst.REDIRECT_PATH,
    )
    if redirect:
        return redirect

    history = get_chat_history(db, project_id)

    resumption = handle_agent_resumption(db, project_id, AgentConst.WORKFLOW_NAME, history, is_start=is_start)
    if resumption:
        return resumption

    # Build the message list for this turn
    messages = list(history) if history else [{"role": "user", "content": "Please analyze and assign tasks."}]

    if user_message:
        save_chat_message(db, project_id, "user", user_message, user_id)
        messages.append({"role": "user", "content": user_message})

    response = _execute_agent(db, user_id, project_id, messages)
    response["status"] = "started" if is_start else "running"
    return response


# ── Auto-assignment ────────────────────────────────────────────────────────────

def run_auto_assignment(db: Session, user_id: UUID, project_id: UUID) -> Dict[str, Any]:
    """Trigger the agent to automatically assign all unassigned tasks in one shot."""
    auto_prompt = (
        "AUTOMATED_TRIGGER: Please fetch all unassigned tasks and project members. "
        "Then, assign all tasks to the best-fit members while balancing the workload."
    )
    save_chat_message(db, project_id, "user", "System Triggered Auto-Assignment")

    set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "thinking")
    agent = TaskAssignerAgent(project_id)

    try:
        history = get_chat_history(db, project_id)
        response = agent.run([*history, {"role": "user", "content": auto_prompt}])
        content = response.get("content")

        if content:
            save_chat_message(db, project_id, "assistant", content)

        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "in_progress")
        return {"status": "success", "message": "Auto-assignment complete.", "content": content}

    except Exception as e:
        logger.exception(f"Auto-assignment failed for project {project_id}: {e}")
        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "in_progress")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

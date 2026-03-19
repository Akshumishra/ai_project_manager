import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.backend.model.project import ProjectMember
from src.backend.model.task_assigner_chat import TaskAssignerChat
from src.backend.utils.workflow_utils import (
    get_workflow_status,
    set_workflow_status,
    check_completion_and_redirect,
    handle_thinking_lock
)
from src.backend.task_assigner.constants import TaskAssignerConstants
from src.backend.task_assigner.task_assigner_agent.agent import TaskAssignerAgent

logger = logging.getLogger(__name__)
AgentConstants = TaskAssignerConstants


def get_task_assigner_chat_history(db: Session, project_id: UUID) -> List[Dict[str, str]]:
    """Fetch persistent chat history for the task assignment phase."""
    try:
        chats = (
            db.query(TaskAssignerChat)
            .filter(TaskAssignerChat.project_id == project_id)
            .order_by(TaskAssignerChat.created_at)
            .all()
        )
        return [{"role": chat.role, "content": chat.content} for chat in chats]
    except Exception as e:
        logger.error(f"Failed to fetch chat history for project {project_id}: {e}")
        return []


def save_task_assigner_chat_message(db: Session, project_id: UUID, role: str, content: str, user_id: UUID | None = None):
    """Save a single chat message to the task_assigner_chats table."""
    try:
        project_member_id = None
        if user_id:
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            ).first()
            if member:
                project_member_id = member.id

        chat = TaskAssignerChat(
            project_id=project_id,
            role=role,
            content=content,
            project_member_id=project_member_id,
        )
        db.add(chat)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save chat message for project {project_id}: {e}")
        db.rollback()


def _execute_task_assigner_agent_turn(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    messages: List[Dict[str, str]]
) -> Dict[str, Any]:
    """Internal orchestrator for task assigner agent execution and result processing."""
    set_workflow_status(db, project_id, AgentConstants.WORKFLOW_NAME, "thinking")
    agent = TaskAssignerAgent(user_id, project_id)

    try:
        response = agent.run(messages)
        content = response.get("content")

        if content:
            save_task_assigner_chat_message(db, project_id, "assistant", content)

        set_workflow_status(db, project_id, AgentConstants.WORKFLOW_NAME, "in_progress")

        return response

    except Exception as e:
        logger.exception(f"Agent execution failed for project {project_id}: {e}")
        set_workflow_status(db, project_id, AgentConstants.WORKFLOW_NAME, "in_progress")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Agent failed: {str(e)}")


def run_task_assigner_agent(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    user_message: str | None = None,
    is_start: bool = False,
):
    """Entry point for the task assigner agent phase."""

    redirect = check_completion_and_redirect(db, project_id, AgentConstants.WORKFLOW_NAME, AgentConstants.REDIRECT_PATH)
    if redirect:
        return redirect

    history = get_task_assigner_chat_history(db, project_id)

    if is_start:
        is_interrupted = history and history[-1]["role"] == "user"
        if is_interrupted and handle_thinking_lock(db, project_id, AgentConstants.WORKFLOW_NAME):
            return {"messages": history, "status": "resumed", "thinking": True}

        if history and not is_interrupted:
            return {
                "status": "resumed",
                "messages": history
            }

    messages = []
    if history:
        messages.extend(history)
    else:
        messages.append({"role": "user", "content": "Please analyze and assign tasks."})

    if user_message:
        save_task_assigner_chat_message(db, project_id, "user", user_message, user_id=user_id)
        messages.append({"role": "user", "content": user_message})

    response = _execute_task_assigner_agent_turn(db, user_id, project_id, messages)

    if is_start and history:
        return {
            "status": "resumed",
            "messages": get_task_assigner_chat_history(db, project_id)
        }

    response["status"] = "started" if is_start else "running"
    return response


def run_auto_assignment(
    db: Session,
    user_id: UUID,
    project_id: UUID
):
    """Triggers the agent to automatically assign all unassigned tasks."""
    set_workflow_status(db, project_id, AgentConstants.WORKFLOW_NAME, "thinking")

    auto_prompt = (
        "AUTOMATED_TRIGGER: Please fetch all unassigned tasks and project members. "
        "Then, assign all tasks to the best-fit members while balancing the workload. "
    )

    save_task_assigner_chat_message(db, project_id, "user", "System Triggered Auto-Assignment")

    try:
        agent = TaskAssignerAgent(user_id, project_id)
        history = get_task_assigner_chat_history(db, project_id)
        messages = [*history, {"role": "user", "content": auto_prompt}]

        response = agent.run(messages)
        content = response.get("content")

        if content:
            save_task_assigner_chat_message(db, project_id, "assistant", content)

        set_workflow_status(db, project_id, AgentConstants.WORKFLOW_NAME, "in_progress")

        return {
            "status": "success",
            "message": "Auto-assignment complete.",
            "content": content
        }
    except Exception as e:
        logger.exception(f"Auto-assignment failed for project {project_id}: {e}")
        set_workflow_status(db, project_id, AgentConstants.WORKFLOW_NAME, "in_progress")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Auto-assignment failed: {str(e)}")

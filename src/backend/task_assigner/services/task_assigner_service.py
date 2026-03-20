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
)
from src.backend.task_assigner.constants import TaskAssignerConstants
from src.backend.task_assigner.task_assigner_agent.agent import TaskAssignerAgent

logger = logging.getLogger(__name__)
AgentConst = TaskAssignerConstants


def get_chat_history(db: Session, project_id: UUID) -> List[Dict[str, str]]:
    return get_agent_chat_history(db, TaskAssignerChat, project_id)


def save_chat_message(db: Session, project_id: UUID, role: str, content: str, user_id: UUID = None):
    save_agent_chat_message(db, TaskAssignerChat, project_id, role, content, user_id)


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
        return {"status": "success", "content": content}

    except Exception as e:
        logger.exception(f"Auto-assignment failed for project {project_id}: {e}")
        set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "in_progress")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

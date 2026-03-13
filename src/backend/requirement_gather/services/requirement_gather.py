from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID

from src.backend.requirement_gather.requirement_agent.agent import RequirementAgent
from src.backend.requirement_gather.services.chat_history import (
    get_chat_history,
    save_chat_message,
    build_initial_user_prompt
)

from src.backend.model.document import Document
from src.backend.model.project import ProjectWorkflowStatus

def start_requirement_agent(db: Session, user_id: UUID, project_id: UUID, background: str = None):
    # 1. Check Workflow Status first for redirection
    wf_status = db.query(ProjectWorkflowStatus).filter(
        ProjectWorkflowStatus.project_id == project_id,
        ProjectWorkflowStatus.workflow_name == "requirement_gathering"
    ).first()

    if wf_status and wf_status.status == "completed":
        return {
            "status": "completed",
            "saved": True,
            "redirect": "/tech-doc"
        }

    history = get_chat_history(db, project_id)
    
    # 2. Self-Healing Chat Resumption
    # If the last message is from 'user', it means the page refreshed before assistant replied.
    # We must trigger the agent reply now so the user isn't stuck.
    is_interrupted = history and history[-1]["role"] == "user"

    if history and not is_interrupted:
        return {
            "messages": history,
            "status": "resumed"
        }

    # build the dynamic personalized context (non-persistent)
    project_context = build_initial_user_prompt(db, project_id, background)

    # Prepare messages for the LLM
    # Note: project_context is prepended as a USER message but NOT saved to DB
    run_messages = [{"role": "user", "content": project_context}]
    if history:
        run_messages.extend(history)
    
    agent = RequirementAgent(user_id, project_id)
    
    try:
        response = agent.run(run_messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")
    
    content = response.get("content")
    
    if not content:
        raise HTTPException(status_code=500, detail="Agent returned empty response")
    
    save_chat_message(
        db=db,
        project_id=project_id,
        role="assistant",
        content=content
    )
    
    if history:
        return {
            "messages": get_chat_history(db, project_id),
            "status": "resumed",
            "saved": response.get("saved", False)
        }

    response["status"] = "started"
    return response

def run_requirement_agent(db: Session, user_id: UUID, project_id: UUID, user_message: str = None, background: str = None):
    history = get_chat_history(db, project_id)
    
    save_chat_message(
        db=db,
        project_id=project_id,
        role="user",
        content=user_message,
        user_id=user_id
    )

    project_context = build_initial_user_prompt(db, project_id, background)

    # Prepare messages for the LLM: dynamic context + persistent history + new message
    run_messages = [
        {"role": "user", "content": project_context},
        *history,
        {"role": "user", "content": user_message}
    ]

    agent = RequirementAgent(user_id, project_id)

    try:
        response = agent.run(run_messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")

    content = response.get("content")

    if not content:
        raise HTTPException(status_code=500, detail="Agent returned empty response")

    save_chat_message(
        db=db,
        project_id=project_id,
        role="assistant",
        content=content
    )

    return response

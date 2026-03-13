from datetime import datetime, timezone, timedelta
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
    is_interrupted = history and history[-1]["role"] == "user"
    
    # Check for concurrency: is the agent already thinking?
    is_thinking = wf_status and wf_status.status == "thinking"
    is_stale = False
    if is_thinking and wf_status.updated_at:
        # If thinking for more than 60 seconds, consider it stale/crashed
        if datetime.now(timezone.utc) - wf_status.updated_at.replace(tzinfo=timezone.utc) > timedelta(seconds=60):
            is_stale = True

    # If it's thinking and NOT stale, just return history (don't trigger healer)
    if is_interrupted and is_thinking and not is_stale:
        return {
            "messages": history,
            "status": "resumed",
            "thinking": True
        }

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
    
    # Set status to thinking for concurrency control during healing
    if not wf_status:
        wf_status = ProjectWorkflowStatus(
            project_id=project_id,
            workflow_name="requirement_gathering",
            status="thinking"
        )
        db.add(wf_status)
    else:
        wf_status.status = "thinking"
    db.commit()

    agent = RequirementAgent(user_id, project_id)
    
    try:
        response = agent.run(run_messages)
    except Exception as e:
        wf_status.status = "in_progress"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")
    
    content = response.get("content")
    
    if not content:
        wf_status.status = "in_progress"
        db.commit()
        raise HTTPException(status_code=500, detail="Agent returned empty response")
    
    save_chat_message(
        db=db,
        project_id=project_id,
        role="assistant",
        content=content
    )
    
    # Reset status only if NOT completed
    is_saved = response.get("saved", False)
    if not is_saved:
        wf_status.status = "in_progress"
        db.commit()

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

    # Set status to thinking for concurrency control
    wf_status = db.query(ProjectWorkflowStatus).filter(
        ProjectWorkflowStatus.project_id == project_id,
        ProjectWorkflowStatus.workflow_name == "requirement_gathering"
    ).first()
    if not wf_status:
        wf_status = ProjectWorkflowStatus(
            project_id=project_id,
            workflow_name="requirement_gathering",
            status="thinking"
        )
        db.add(wf_status)
    else:
        wf_status.status = "thinking"
    db.commit()

    agent = RequirementAgent(user_id, project_id)

    try:
        response = agent.run(run_messages)
        
        content = response.get("content")
        if not content:
            raise HTTPException(status_code=500, detail="Agent returned empty response")

        save_chat_message(
            db=db,
            project_id=project_id,
            role="assistant",
            content=content
        )
        
        # Reset status ONLY if it wasn't marked as completed by a tool
        is_saved = response.get("saved", False)
        if not is_saved:
            wf_status.status = "in_progress"
            db.commit()
        return response

    except Exception as e:
        # Reset on error to allow retry
        wf_status.status = "in_progress"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")

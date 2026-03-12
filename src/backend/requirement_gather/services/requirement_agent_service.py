from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.backend.requirement_gather.requirement_agent.agent import RequirementAgent
from src.backend.requirement_gather.services.helping_functions import (
    get_chat_history,
    save_chat_message,
    build_initial_user_prompt
)

def start_requirement_agent(db: Session, user_id: str, project_id: str, background: str = None):
    history = get_chat_history(db, project_id)
    
    if history:
        raise HTTPException(status_code=400, detail="Chat history already exists. Use run_requirement_agent to continue.")
    
    user_message = build_initial_user_prompt(db, project_id, background)
    
    save_chat_message(
        db=db,
        project_id=project_id,
        role="user",
        content=user_message,
        user_id=user_id
    )
    
    history.append({
        "role": "user",
        "content": user_message
    })
    
    agent = RequirementAgent(user_id, project_id)
    
    try:
        response = agent.run(history)
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

def run_requirement_agent(db: Session, user_id: str, project_id: str, user_message: str = None, background: str = None):
    history = get_chat_history(db, project_id)
    

    save_chat_message(
        db=db,
        project_id=project_id,
        role="user",
        content=user_message,
        user_id=user_id
    )

    history.append({
        "role": "user",
        "content": user_message
    })

    agent = RequirementAgent(user_id, project_id)

    try:
        response = agent.run(history)
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

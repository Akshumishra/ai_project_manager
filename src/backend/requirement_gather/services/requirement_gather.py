from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID

from src.backend.requirement_gather.requirement_agent.agent import RequirementAgent
from src.backend.requirement_gather.services.chat_history import (
    get_chat_history,
    save_chat_message,
    build_initial_user_prompt
)
from src.backend.utils.workflow_utils import (
    set_workflow_status,
    check_completion_and_redirect,
    handle_thinking_lock
)
from src.backend.requirement_gather.constants import RequirementAgentConstants
from src.backend.utils.workflow_utils import get_workflow_status
from src.backend.requirement_gather.requirement_agent.tools.get_current_requirement_draft import get_requirement_draft_tool


AGENT_CONST = RequirementAgentConstants

def _execute_agent_run(db: Session, user_id: UUID, project_id: UUID, run_messages: List[Dict[str, str]], is_recovering: bool = False) -> Dict[str, Any]:
    """Internal helper to execute the agent, save output, and manage thinking lock."""
    set_workflow_status(db, project_id, AGENT_CONST.WORKFLOW_NAME, "thinking")
    agent = RequirementAgent(user_id, project_id)
    
    try:
        response = agent.run(run_messages)
        content = response.get("content")
        
        if not content:
            raise HTTPException(status_code=500, detail="Agent returned empty response")
        
        save_chat_message(db=db, project_id=project_id, role="assistant", content=content)
        
        if not response.get("saved", False):
            set_workflow_status(db, project_id, AGENT_CONST.WORKFLOW_NAME, "in_progress")
            
        if is_recovering:
            return {
                "messages": get_chat_history(db, project_id),
                "status": "resumed",
                "saved": response.get("saved", False),
                "document": response.get("doc")
            }
        
        workflow_status = get_workflow_status(db, project_id, AGENT_CONST.WORKFLOW_NAME)
        if workflow_status:
            response["status"] = workflow_status.status
        
        if "doc" in response:
            response["document"] = response.pop("doc")

        return response

    except Exception as e:
        set_workflow_status(db, project_id, AGENT_CONST.WORKFLOW_NAME, "in_progress")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")

def start_requirement_agent(db: Session, user_id: UUID, project_id: UUID, background: str = None):
    """Entry point for starting or resuming the requirement gathering session."""
    
    redirect = check_completion_and_redirect(db, project_id, AGENT_CONST.WORKFLOW_NAME, AGENT_CONST.REDIRECT_PATH)
    if redirect:
        return redirect

    history = get_chat_history(db, project_id)
    is_interrupted = history and history[-1]["role"] == "user"
    
    if is_interrupted and handle_thinking_lock(db, project_id, AGENT_CONST.WORKFLOW_NAME):
        return {"messages": history, "status": "resumed", "thinking": True}
        

    if history and not is_interrupted:
        get_draft_tool = get_requirement_draft_tool(project_id)
        current_doc = get_draft_tool.invoke({})
        if "draft found" in current_doc or "no content" in current_doc or "Error" in current_doc:
            current_doc = ""

        return {
            "messages": history, 
            "status": "resumed",
            "document": current_doc
        }

    project_context = build_initial_user_prompt(db, project_id, background)
    run_messages = [{"role": "user", "content": project_context}]
    if history:
        run_messages.extend(history)
    
    result = _execute_agent_run(db, user_id, project_id, run_messages, is_recovering=is_interrupted)
    if not is_interrupted:
        result["status"] = "started"
    return result

def run_requirement_agent(db: Session, user_id: UUID, project_id: UUID, user_message: str, background: str = None):
    """Process a new user message in the requirement gathering session."""
    
    save_chat_message(db=db, project_id=project_id, role="user", content=user_message, user_id=user_id)
    
    history = get_chat_history(db, project_id)
    project_context = build_initial_user_prompt(db, project_id, background)
    
    run_messages = [{"role": "user", "content": project_context}, *history]
    
    return _execute_agent_run(db, user_id, project_id, run_messages)

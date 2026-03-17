import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from src.backend.model.document import Document, DocumentBlock
from src.backend.model.project import ProjectMember, ProjectWorkflowStatus
from src.backend.model.tech_doc_chat import TechDocChat
from src.backend.technical_doc.document_sections import build_project_document_title
from src.backend.utils.get_project_details import get_project_detail
from src.backend.utils.workflow_utils import (
    get_workflow_status,
    set_workflow_status,
    check_completion_and_redirect,
    handle_thinking_lock
)
from src.backend.technical_doc.constants import TechDocAgentConstants
from src.backend.technical_doc.services.save_tech_doc import save_technical_spec_in_db

# Configure logging
logger = logging.getLogger(__name__)
AgentConstants = TechDocAgentConstants

def get_tech_doc_chat_history(db: Session, project_id: UUID) -> List[Dict[str, str]]:
    """Fetch persistent chat history for the tech doc phase."""
    try:
        chats = (
            db.query(TechDocChat)
            .filter(TechDocChat.project_id == project_id)
            .order_by(TechDocChat.created_at)
            .all()
        )
        return [{"role": chat.role, "content": chat.content} for chat in chats]
    except Exception as e:
        logger.error(f"Failed to fetch chat history for project {project_id}: {e}")
        return []

def save_tech_doc_chat_message(db: Session, project_id: UUID, role: str, content: str, user_id: UUID | None = None):
    """Save a single chat message to the tech_doc_chats table."""
    try:
        project_member_id = None
        if user_id:
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            ).first()
            if member:
                project_member_id = member.id

        chat = TechDocChat(
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

def fetch_document_text_by_label(db: Session, project_id: UUID, label: str) -> str:
    """Generic helper to fetch document text by its label."""
    try:
        doc_title = build_project_document_title(db, project_id, label)
        project_title = get_project_detail(db, project_id).get("project_title", "")
        
        possible_titles = [
            doc_title,
            f"{project_title} - {label}",
            f"{project_title} - {label} Specification",
            label,
            f"{label} Specification"
        ]

        doc = db.query(Document).filter(
            Document.project_id == project_id,
            Document.title.in_(possible_titles),
        ).first()

        if not doc:
            return ""

        blocks = db.query(DocumentBlock).filter(
            DocumentBlock.doc_id == doc.id
        ).order_by(DocumentBlock.position_key).all()
        
        return "\n\n".join(block.content for block in blocks if block.content).strip()
    except Exception as e:
        logger.error(f"Error fetching document with label {label} for project {project_id}: {e}")
        return ""

def fetch_requirement_specification_text(db: Session, project_id: UUID) -> str:
    """Retrieves the full requirement spec text to serve as agent context."""
    text = fetch_document_text_by_label(db, project_id, AgentConstants.REQ_DOC_LABEL)
    return text if text else "No Requirement Specification found for this project."

def fetch_technical_specification_text(db: Session, project_id: UUID) -> str:
    """Retrieves the current technical spec draft text."""
    return fetch_document_text_by_label(db, project_id, AgentConstants.TECH_DOC_LABEL)

def build_initial_user_prompt(db: Session, project_id: UUID) -> str:
    """Constructs the starting context for the TechDoc agent."""
    project_detail = get_project_detail(db, project_id)
    project_title = project_detail.get("project_title", "Untitled Project")
    requirements_text = fetch_requirement_specification_text(db, project_id)

    return (
        f"Project Title: {project_title}\n\n"
        f"Requirements:\n{requirements_text}\n\n"
        "Please generate the first draft of the technical specification and greet the user."
    )

def _execute_tech_doc_agent_turn(
    db: Session, 
    user_id: UUID, 
    project_id: UUID, 
    messages: List[Dict[str, str]], 
    current_doc: Optional[str] = None
) -> Dict[str, Any]:
    """Internal orchestrator for tech doc agent execution and result processing."""
    from src.backend.technical_doc.tech_doc_agent.agent import TechDocAgent
    
    set_workflow_status(db, project_id, AgentConstants.WORKFLOW_NAME, "thinking")
    agent = TechDocAgent(user_id, project_id)
    
    try:
        response = agent.run(messages)
        updated_doc = response.get("document")
            
        if updated_doc:
            response["document"] = updated_doc
            try:
                save_technical_spec_in_db(
                    db=db,
                    user_id=user_id,
                    project_id=project_id,
                    markdown_content=updated_doc
                )
            except Exception as save_err:
                logger.error(f"Auto-save of technical spec failed for project {project_id}: {save_err}")

        if response.get("content"):
            save_tech_doc_chat_message(db, project_id, "assistant", response["content"])

        set_workflow_status(db, project_id, AgentConstants.WORKFLOW_NAME, "in_progress")
        
        return response

    except Exception as e:
        logger.exception(f"Agent execution failed for project {project_id}: {e}")
        set_workflow_status(db, project_id, AgentConstants.WORKFLOW_NAME, "in_progress")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Agent failed: {str(e)}")

def run_tech_doc_agent(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    user_message: str | None = None,
    current_document_markdown: Optional[str] = None,
    is_start: bool = False,
):
    """Entry point for the technical documentation agent phase."""
    
    # 1. Prerequisite Checks
    req_status = get_workflow_status(db, project_id, AgentConstants.REQ_WORKFLOW_NAME)
    logger.info(f"Prerequisite check for project {project_id}: workflow={AgentConstants.REQ_WORKFLOW_NAME}, status={req_status.status if req_status else 'None'}")
    
    if not req_status or req_status.status != "completed":
        return {
            "status": "prerequisite_missing",
            "redirect": "/requirement-agent",
            "message": f"Please complete the Requirement Gathering phase first. Current status: {req_status.status if req_status else 'Not started'}"
        }

    redirect = check_completion_and_redirect(db, project_id, AgentConstants.WORKFLOW_NAME, AgentConstants.REDIRECT_PATH)
    if redirect:
        return redirect

    history = get_tech_doc_chat_history(db, project_id)
    
    # 2. Resumption / Concurrency Handling
    if is_start:
        is_interrupted = history and history[-1]["role"] == "user"
        if is_interrupted and handle_thinking_lock(db, project_id, AgentConstants.WORKFLOW_NAME):
            return {"messages": history, "status": "resumed", "thinking": True}
        
        if history and not is_interrupted:
            return {
                "status": "resumed",
                "messages": history, 
                "document": fetch_technical_specification_text(db, project_id)
            }

    if not current_document_markdown:
        current_document_markdown = fetch_technical_specification_text(db, project_id)

    # 3. Context Preparation
    messages = [{"role": "user", "content": build_initial_user_prompt(db, project_id)}]
    if history:
        messages.extend(history)

    if current_document_markdown and current_document_markdown.strip():
        messages.append({"role": "user", "content": f"Current technical document draft:\n\n{current_document_markdown}"})

    if user_message:
        save_tech_doc_chat_message(db, project_id, "user", user_message, user_id=user_id)
        messages.append({"role": "user", "content": user_message})

    # 4. Agent Execution
    response = _execute_tech_doc_agent_turn(db, user_id, project_id, messages, current_document_markdown)
    
    if is_start and history:
        return {
            "status": "resumed",
            "messages": get_tech_doc_chat_history(db, project_id),
            "document": response.get("document")
        }

    response["status"] = "started" if is_start else "running"
    return response

def save_final_tech_doc(db: Session, user_id: UUID, project_id: UUID, document_markdown: str, background_tasks: BackgroundTasks = None):
    """Explicitly saves the technical document and updates workflow status to completed."""
    try:
        result = save_technical_spec_in_db(
            db=db,
            user_id=user_id,
            project_id=project_id,
            markdown_content=document_markdown,
            background_tasks=background_tasks
        )
        
        if result.get("success"):
            return {"status": "success", "message": result.get("message")}
        else:
            logger.error(f"Failed to finalize tech doc for project {project_id}: {result.get('message')}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message"))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while saving final tech doc for project {project_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An unexpected error occurred while saving the document.")

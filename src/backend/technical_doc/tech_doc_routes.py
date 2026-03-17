from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_db
from src.backend.technical_doc.services.tech_doc_service import (
    run_tech_doc_agent,
    save_final_tech_doc
)
from .schemas import (
    TechDocAgentRequest, 
    SaveTechDocRequest,
    TechDocResponseSchema,
    TechDocSaveResponseSchema
)

router = APIRouter(prefix="/api/technical-doc", tags=["Technical Doc"])

@router.get(
    "/projects/{project_id}/tech-doc-agent",
    response_model=TechDocResponseSchema
)
async def start_tech_doc_agent(
    project_id: UUID, 
    user_id: UUID, 
    db: Session = Depends(get_db)
):
    """
    Initializes or resumes the Tech Doc agent for a specific project.
    """
    try:
        response = run_tech_doc_agent(
            db=db,
            user_id=user_id,
            project_id=project_id,
            user_message=None,
            is_start=True
        )
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start tech doc agent: {str(e)}"
        )

@router.post(
    "/projects/{project_id}/tech-doc-agent",
    response_model=TechDocResponseSchema
)
async def run_agent_turn(
    project_id: UUID, 
    request: TechDocAgentRequest, 
    db: Session = Depends(get_db)
):
    """
    Continues a chat session with the Tech Doc agent.
    """
    try:
        response = run_tech_doc_agent(
            db=db,
            user_id=request.user_id,
            project_id=project_id,
            user_message=request.message,
            current_document_markdown=request.current_document_markdown,
            is_start=False
        )
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error during agent execution: {str(e)}"
        )

@router.post(
    "/projects/{project_id}/tech-doc",
    response_model=TechDocSaveResponseSchema
)
async def save_tech_doc(
    project_id: UUID, 
    request: SaveTechDocRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Finalizes and saves the technical document.
    """
    try:
        response = save_final_tech_doc(
            db=db,
            user_id=request.user_id,
            project_id=project_id,
            document_markdown=request.document_markdown,
            background_tasks=background_tasks
        )
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save technical document: {str(e)}"
        )

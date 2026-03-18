from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_db
from src.backend.technical_doc.services.tech_doc_service import (
    run_tech_doc_agent,
    save_final_tech_doc
)
from src.backend.task_creator import task_creator_service as task_creator_services
from src.backend.slack.slack_service import setup_slack_channel_for_project
from .schemas import (
    TechDocAgentRequest, 
    SaveTechDocRequest,
    TechDocResponseSchema,
    TechDocSaveResponseSchema
)

router = APIRouter(prefix="/projects", tags=["Technical Doc"])

@router.get(
    "/{project_id}/tech-doc-agent",
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.post(
    "/{project_id}/tech-doc-agent",
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.post(
    "/{project_id}/tech-doc",
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
        # Fetch project name for Slack channel creation
        from src.backend.model.project import Project
        project = db.query(Project).filter(Project.id == project_id).first()
        project_name = project.name if project else str(project_id)

        response = save_final_tech_doc(
            db=db,
            user_id=request.user_id,
            project_id=project_id,
            document_markdown=request.document_markdown,
            background_tasks=background_tasks
        )

        # Auto-trigger task generation in background
        background_tasks.add_task(
            task_creator_services.generate_and_save_tasks,
            project_id,
            request.user_id
        )

        # Auto-create Slack channel + bot join if not already set
        if project and not project.slack_channel_id:
            background_tasks.add_task(
                setup_slack_channel_for_project,
                project_id,
                project_name
            )

        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

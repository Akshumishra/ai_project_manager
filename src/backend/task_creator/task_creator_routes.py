from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User
from src.backend.utils.workflow_utils import get_workflow_status
from . import task_creator_service as task_creator_services
from .schemas import TaskGenerationResponse
from .constants import TaskCreatorConstants

router = APIRouter(prefix="/api/task-creator", tags=["Task Creator"])

@router.post(
    "/projects/{project_id}/generate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskGenerationResponse
)
async def generate_project_tasks(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger AI-driven task generation for a specific project.

    This process runs in the background to analyze project documentation
    (Requirements and Technical Specifications) and generate an initial set of tasks.
    """
    try:
        background_tasks.add_task(task_creator_services.generate_and_save_tasks, project_id, current_user.id)
        return {
            "status": "success",
            "message": "Task generation has been initiated in the background."
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/projects/{project_id}/status",
    status_code=status.HTTP_200_OK,
)
async def get_task_generation_status(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Poll the status of the AI task generation background job.
    Returns one of: not_started | generating | completed | failed | failed_missing_docs
    """
    wf_status = get_workflow_status(db, project_id, TaskCreatorConstants.WORKFLOW_NAME)
    if not wf_status:
        return {"status": "not_started", "message": "Task generation has not been initiated yet."}

    status_map = {
        "generating": "Task generation is in progress...",
        "completed": "Tasks have been generated successfully.",
        "failed": "Task generation failed. Please try again.",
        "failed_missing_docs": "Missing required documents (Requirement or Technical Specification). Please complete them first.",
    }

    return {
        "status": wf_status.status,
        "message": status_map.get(wf_status.status, wf_status.status),
    }

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

from src.backend.utils.queue_utils import get_queue

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
    Uses Redis Queue (RQ) if available, falling back to BackgroundTasks.
    """
    try:
        # Try to use RQ
        queue = get_queue()
        if queue:
            queue.enqueue(
                task_creator_services.generate_and_save_tasks,
                project_id,
                current_user.id,
                job_id=f"task-gen-{project_id}",
                job_timeout=600,   # 10 minutes — AI generation can take time
                result_ttl=86400,  # Keep result for 24h
                failure_ttl=86400, # Keep failed job info for 24h for debugging
            )
            message = "Task generation has been initiated via background queue."
        else:
            # Fallback to local background tasks if Redis/RQ is not available
            background_tasks.add_task(task_creator_services.generate_and_save_tasks, project_id, current_user.id)
            message = "Task generation has been initiated (local fallback)."

        return {
            "status": "success",
            "message": message
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

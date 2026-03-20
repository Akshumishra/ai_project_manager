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
from src.backend.config import settings

router = APIRouter(prefix="/api/task-creator", tags=["Task Creator"])


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
        "thinking": "Task generation is in progress...",
        "completed": "Tasks have been generated successfully.",
        "in_progress": "Ready to generate tasks.",
    }

    # Ensure we return a string status for the frontend
    current_status = wf_status.status.value if hasattr(wf_status.status, "value") else str(wf_status.status)

    return {
        "status": current_status,
        "message": status_map.get(current_status, current_status),
    }

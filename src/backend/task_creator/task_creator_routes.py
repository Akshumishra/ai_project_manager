from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User
from . import task_creator_service as task_creator_services
from .schemas import TaskGenerationResponse

router = APIRouter(prefix="/api/task-creator", tags=["Task Creator"])

@router.post(
    "/projects/{project_id}/generate",
    status_code=202,
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
        # Pass user_id to service to initialize the agent
        background_tasks.add_task(task_creator_services.generate_and_save_tasks, project_id, current_user.id)
        return {
            "status": "success", 
            "message": "Task generation has been initiated in the background."
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to trigger task generation: {str(e)}"
        )

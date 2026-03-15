from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User
from . import task_creator_services

router = APIRouter(prefix="/api/task-creator", tags=["Task Creator"])

@router.post("/projects/{project_id}/generate")
def generate_project_tasks(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger task generation for a project.
    """
    background_tasks.add_task(task_creator_services.generate_and_save_tasks, db, project_id)
    return {"status": "success", "message": "Task generation started in background."}

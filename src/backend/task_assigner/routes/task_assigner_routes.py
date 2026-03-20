from fastapi import APIRouter, Depends
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_db
from src.backend.task_assigner.services.task_assigner_service import (
    run_auto_assignment,
)
from src.backend.task_assigner.schemas import TaskAssignerResponseSchema

router = APIRouter(prefix="/api/task-assigner", tags=["Task Assigner"])


@router.post("/projects/{project_id}/auto-assign", response_model=dict)
async def auto_assign_tasks(
    project_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Automated one-click task assignment for the entire project team."""
    return run_auto_assignment(db, current_user.id, project_id)

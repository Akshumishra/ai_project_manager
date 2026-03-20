from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_db
from src.backend.task_assigner.services.task_assigner_service import (
    run_task_assigner_agent,
    run_auto_assignment,
)
from src.backend.task_assigner.schemas import TaskAssignerAgentRequest, TaskAssignerResponseSchema

router = APIRouter(prefix="/api/task-assigner", tags=["Task Assigner"])


@router.get("/projects/{project_id}/agent", response_model=TaskAssignerResponseSchema)
async def start_task_assigner(project_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    """Initialize or resume the Task Assigner agent session."""
    return run_task_assigner_agent(db=db, user_id=user_id, project_id=project_id, is_start=True)


@router.post("/projects/{project_id}/agent", response_model=TaskAssignerResponseSchema)
async def run_task_assigner_turn(
    project_id: UUID,
    request: TaskAssignerAgentRequest,
    db: Session = Depends(get_db),
):
    """Continue a chat session with the Task Assigner agent."""
    return run_task_assigner_agent(
        db=db,
        user_id=request.user_id,
        project_id=project_id,
        user_message=request.message,
        is_start=False,
    )


@router.post("/projects/{project_id}/auto-assign", response_model=dict)
async def auto_assign_tasks(project_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    """Automated one-click task assignment for the entire project team."""
    return run_auto_assignment(db, user_id, project_id)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.db.database import get_db
from src.backend.task_assigner.services.task_assigner_service import run_task_assigner_agent
from src.backend.task_assigner.schemas import TaskAssignerAgentRequest, TaskAssignerResponseSchema

router = APIRouter(prefix="/api/task-assigner", tags=["Task Assigner"])


@router.get(
    "/projects/{project_id}/agent",
    response_model=TaskAssignerResponseSchema
)
async def start_task_assigner_agent(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Initializes or resumes the Task Assigner agent.
    """
    try:
        response = run_task_assigner_agent(
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
            detail=f"Failed to start task assigner agent: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/agent",
    response_model=TaskAssignerResponseSchema
)
async def run_agent_turn(
    project_id: UUID,
    request: TaskAssignerAgentRequest,
    db: Session = Depends(get_db)
):
    """
    Continues a chat session with the Task Assigner agent.
    """
    try:
        response = run_task_assigner_agent(
            db=db,
            user_id=request.user_id,
            project_id=project_id,
            user_message=request.message,
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
    "/projects/{project_id}/auto-assign",
    response_model=dict
)
async def auto_assign_tasks(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Automated one-click task assignment for the entire project team.
    """
    try:
        from src.backend.task_assigner.services.task_assigner_service import run_auto_assignment
        return run_auto_assignment(db, user_id, project_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auto-assignment failed: {str(e)}"
        )

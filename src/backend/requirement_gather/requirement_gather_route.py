from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User
from src.backend.requirement_gather.services.requirement_gather import (
    run_requirement_agent,
    start_requirement_agent,
    complete_requirement_step,
)
from src.backend.requirement_gather.schemas import (
    RequirementAgentRequest,
    RequirementAgentResponse,
    StandardResponse
)

router = APIRouter(prefix="/api/agent/projects", tags=["projects"])

@router.post("/{project_id}/requirement-agent", response_model=RequirementAgentResponse, status_code=status.HTTP_200_OK)
def run_agent(
    project_id: UUID,
    request: RequirementAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process a user message through the requirement gathering agent.
    """
    return run_requirement_agent(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
        user_message=request.message
    )


@router.get("/{project_id}/requirement-agent", response_model=RequirementAgentResponse, status_code=status.HTTP_200_OK)
def start_agent(
    project_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initialize or resume the requirement gathering session for a project.
    Checks if a draft exists and returns it along with chat history.
    """
    return start_requirement_agent(
        db=db,
        user_id=current_user.id,
        project_id=project_id
    )


@router.patch("/{project_id}/requirement-complete", response_model=StandardResponse, status_code=status.HTTP_200_OK)
def mark_requirement_complete(
    project_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark the requirement gathering phase as completed in the workflow.
    """
    return complete_requirement_step(db, project_id)

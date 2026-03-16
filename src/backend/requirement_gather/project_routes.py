from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_db
from src.backend.requirement_gather.services.requirement_gather import (
    run_requirement_agent,
    start_requirement_agent,
)
from src.backend.requirement_gather.services.project import create_project_with_owner
from src.backend.requirement_gather.schemas import CreateProjectRequest, RequirementAgentRequest, SaveRequirementRequest
from src.backend.utils.get_project_details import get_project_detail
from src.backend.requirement_gather.services.save_requirement import save_requirement_spec_in_db
from src.backend.requirement_gather.services.save_requirement import complete_requirement_step

router = APIRouter()


@router.post("/projects")
def create_project(request: CreateProjectRequest, db: Session = Depends(get_db)):
    project = create_project_with_owner(
        db=db,
        user_id=request.user_id,
        project_title=request.project_title,
        project_description=request.project_description,
        background=request.background
    )

    return project


@router.get("/projects/{project_id}")
def get_project(project_id: UUID, db: Session = Depends(get_db)):
    project = get_project_detail(db, project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.post("/projects/{project_id}/requirement-agent")
def run_agent(
    project_id: UUID,
    request: RequirementAgentRequest,
    db: Session = Depends(get_db)
):

    response = run_requirement_agent(
        db=db,
        user_id=request.user_id,
        project_id=project_id,
        user_message=request.message
    )

    return response


@router.get("/projects/{project_id}/requirement-agent")
def start_agent(
    project_id: UUID,
    user_id: UUID,
    background: str | None = None,
    db: Session = Depends(get_db)
):
    response = start_requirement_agent(
        db=db,
        user_id=user_id,
        project_id=project_id,
        background=background
    )

    return response


@router.post("/projects/{project_id}/requirement-doc")
def save_requirement_doc(
    project_id: UUID,
    request: SaveRequirementRequest,
    db: Session = Depends(get_db)
):
    
    success, message = save_requirement_spec_in_db(
        db=db,
        user_id=request.user_id,
        project_id=project_id,
        problem_the_project_solves=request.problem_the_project_solves,
        target_users=request.target_users,
        project_goal=request.project_goal,
        key_system_capabilities=request.key_system_capabilities,
        expected_outcome=request.expected_outcome,
        major_constraints=request.major_constraints,
        additional_notes=request.additional_notes
    )

    if not success:
        raise HTTPException(status_code=500, detail=message)

    return {"status": "success", "message": message}

@router.patch("/projects/{project_id}/requirement-complete")
def mark_requirement_complete(project_id: UUID, db: Session = Depends(get_db)):
    success, message = complete_requirement_step(db, project_id)
    if not success:
        raise HTTPException(status_code=500, detail=message)
    return {"status": "success", "message": message}

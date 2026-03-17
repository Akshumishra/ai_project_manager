from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_db
from src.backend.requirement_gather.services.requirement_gather import (
    run_requirement_agent,
    start_requirement_agent,
)
from src.backend.requirement_gather.services.project import create_project_with_owner
from src.backend.requirement_gather.schemas import (
    CreateProjectRequest, 
    RequirementAgentRequest, 
    SaveRequirementRequest,
    ProjectResponse,
    RequirementAgentResponse,
    StandardResponse
)
from src.backend.utils.get_project_details import get_project_detail
from src.backend.requirement_gather.services.save_requirement import (
    save_requirement_spec_document,
    complete_requirement_step
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(request: CreateProjectRequest, db: Session = Depends(get_db)):
    """
    Create a new project and assign the requester as the owner.
    """
    try:
        project = create_project_with_owner(
            db=db,
            user_id=request.user_id,
            project_title=request.project_title,
            project_description=request.project_description,
            background=request.background
        )
        return project
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        db.close()


@router.get("/{project_id}", response_model=ProjectResponse, status_code=status.HTTP_200_OK)
def get_project(project_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve details for a specific project.
    """
    try:
        project = get_project_detail(db, project_id)

        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        return project
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        db.close()


@router.post("/{project_id}/requirement-agent", response_model=RequirementAgentResponse, status_code=status.HTTP_200_OK)
def run_agent(
    project_id: UUID,
    request: RequirementAgentRequest,
    db: Session = Depends(get_db)
):
    """
    Process a user message through the requirement gathering agent.
    """
    try:
        response = run_requirement_agent(
            db=db,
            user_id=request.user_id,
            project_id=project_id,
            user_message=request.message
        )
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        db.close()


@router.get("/{project_id}/requirement-agent", response_model=RequirementAgentResponse, status_code=status.HTTP_200_OK)
def start_agent(
    project_id: UUID,
    user_id: UUID,
    background: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Initialize or resume the requirement gathering session for a project.
    Checks if a draft exists and returns it along with chat history.
    """
    try:
        response = start_requirement_agent(
            db=db,
            user_id=user_id,
            project_id=project_id,
            background=background
        )
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        db.close()


@router.post("/{project_id}/requirement-doc", response_model=StandardResponse, status_code=status.HTTP_200_OK)
def save_requirement_doc(
    project_id: UUID,
    request: SaveRequirementRequest,
    db: Session = Depends(get_db)
):
    """
    Save the collective requirement specification into the database and sync with documents.
    """
    try:
        result = save_requirement_spec_document(
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
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        db.close()


@router.patch("/{project_id}/requirement-complete", response_model=StandardResponse, status_code=status.HTTP_200_OK)
def mark_requirement_complete(project_id: UUID, db: Session = Depends(get_db)):
    """
    Mark the requirement gathering phase as completed in the workflow.
    """
    try:
        result = complete_requirement_step(db, project_id)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        db.close()

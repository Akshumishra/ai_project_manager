from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from . import schemas, services
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get(
    "/",
    response_model=List[schemas.ProjectResponse],
    status_code=status.HTTP_200_OK
)
def get_projects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        return services.get_projects(db, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}"
        )


@router.post(
    "/",
    response_model=schemas.ProjectResponse,
    status_code=status.HTTP_201_CREATED
)
def create_project(
    data: schemas.ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.create_project(data, db, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get(
    "/{project_id}/documents",
    response_model=List[schemas.ProjectDocumentResponse],
    status_code=status.HTTP_200_OK
)
def get_project_documents(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.get_project_documents(project_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project documents: {str(e)}"
        )


@router.post(
    "/{project_id}/members",
    response_model=schemas.MessageResponse,
    status_code=status.HTTP_201_CREATED
)
def add_project_member(
    project_id: UUID,
    data: schemas.AddMemberRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.add_project_member(
            project_id, data, background_tasks, db, current_user
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add project member: {str(e)}"
        )


@router.delete(
    "/{project_id}",
    response_model=schemas.MessageResponse,
    status_code=status.HTTP_200_OK
)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.delete_project(project_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )

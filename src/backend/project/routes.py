from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from . import schemas, services
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("/", response_model=List[schemas.ProjectRead])
def get_projects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return services.get_projects(db, current_user)


@router.post(
    "/", response_model=schemas.ProjectRead, status_code=status.HTTP_201_CREATED
)
def create_project(
    data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return services.create_project(data, db, current_user)


@router.get("/{project_id}/documents")
def get_project_documents(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return services.get_project_documents(project_id, db, current_user)


@router.post("/{project_id}/members")
def add_project_member(
    project_id: UUID,
    data: schemas.AddMemberRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return services.add_project_member(
        project_id, data, background_tasks, db, current_user
    )

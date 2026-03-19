from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from . import schemas, services
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User
from src.backend.model.project import Project as ProjectModel
from src.backend.slack.slack_service import setup_slack_channel_for_project
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("/", response_model=List[schemas.ProjectResponse], status_code=status.HTTP_200_OK)
def get_projects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        return services.get_projects(db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{project_id}", response_model=schemas.ProjectResponse, status_code=status.HTTP_200_OK)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.get_project(project_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{project_id}/status", response_model=schemas.ProjectStatusRead, status_code=status.HTTP_200_OK)
def get_project_status(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.get_project_status(project_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project status {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.patch("/{project_id}/status", response_model=schemas.ProjectResponse, status_code=status.HTTP_200_OK)
def update_project_status(
    project_id: UUID,
    data: schemas.ProjectStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.update_project_status(project_id, data, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project status {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post(
    "/", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED
)
def create_project(
    data: schemas.ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.create_project(data, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{project_id}/documents", status_code=status.HTTP_200_OK)
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
        logger.error(f"Error fetching documents for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/{project_id}/members", response_model=schemas.MemberRead, status_code=status.HTTP_201_CREATED)
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
        logger.error(f"Error adding member to project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{project_id}/members", response_model=List[schemas.MemberRead], status_code=status.HTTP_200_OK)
def get_project_members(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.get_project_members(project_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching members for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/{project_id}/tasks/{task_id}",
    response_model=schemas.TaskRead,
    status_code=status.HTTP_200_OK
)
def get_project_task(
    project_id: UUID,
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.get_project_task(project_id, task_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching task {task_id} for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/{project_id}/tasks",
    response_model=List[schemas.TaskRead],
    status_code=status.HTTP_200_OK
)
def get_project_tasks(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.get_project_tasks(project_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tasks for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post(
    "/{project_id}/tasks",
    response_model=schemas.TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project_task(
    project_id: UUID,
    data: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.create_project_task(project_id, data, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{project_id}/tasks/{task_id}/logs", response_model=List[schemas.TaskLogRead], status_code=status.HTTP_200_OK)
def get_task_logs(
    project_id: UUID,
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.get_task_logs(task_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching logs for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{project_id}/standups", response_model=List[schemas.StandupRead], status_code=status.HTTP_200_OK)
def get_project_standups(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.get_project_standups(project_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching standups for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.patch("/{project_id}/tasks/{task_id}", response_model=schemas.TaskRead, status_code=status.HTTP_200_OK)
def update_project_task(
    project_id: UUID,
    task_id: UUID,
    data: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.update_project_task(project_id, task_id, data, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
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
        logger.error(f"Error deleting project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/{project_id}/slack-url",
    response_model=schemas.SlackChannelResponse,
    status_code=status.HTTP_200_OK
)
def get_slack_join_url(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.get_slack_join_url(project_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Slack URL for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.patch(
    "/{project_id}/slack-channel",
    response_model=schemas.ProjectResponse,
    status_code=status.HTTP_200_OK
)
def set_slack_channel(
    project_id: UUID,
    data: schemas.SlackChannelSetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return services.set_slack_channel(project_id, data, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting Slack channel for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post(
    "/{project_id}/slack-setup",
    status_code=status.HTTP_200_OK
)
def slack_setup(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger Slack channel creation + bot join for a project."""
    try:

        project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        if project.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can set up Slack"
            )

        background_tasks.add_task(setup_slack_channel_for_project, project_id, project.name)
        return {"message": "Slack channel setup started in background", "project_id": str(project_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Slack setup for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

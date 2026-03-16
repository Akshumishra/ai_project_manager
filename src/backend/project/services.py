from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, BackgroundTasks
from uuid import UUID
from . import schemas, utils
from src.backend.model.project import Project, ProjectMember, ProjectWorkflowStatus
from src.backend.model.document import Document
from src.backend.model.user import User
from src.backend.model.task import (
    Task,
    TaskCategory,
    TaskComplexity,
    TaskPriority,
    TaskStatus,
)
from typing import List


def get_projects(db: Session, current_user: User):
    projects = (
        db.query(Project)
        .outerjoin(ProjectMember)
        .filter(
            (Project.created_by == current_user.id)
            | (ProjectMember.user_id == current_user.id),
            Project.deleted_at.is_(None)
        )
        .all()
    )
    return projects


def get_project(project_id: UUID, db: Session, current_user: User):
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
        )
        .first()
    )

    if project.created_by != current_user.id and not is_member:
        raise HTTPException(status_code=403, detail="Access denied to this project")

    return project


def get_project_status(project_id: UUID, db: Session, current_user: User):
    _ensure_project_access(project_id, db, current_user)
    statuses = (
        db.query(ProjectWorkflowStatus)
        .filter(ProjectWorkflowStatus.project_id == project_id)
        .all()
    )
    return {"project_id": project_id, "workflows": statuses}


def create_project(data: schemas.ProjectCreate, db: Session, current_user: User):
    new_project = Project(
        name=data.name, description=data.description, created_by=current_user.id
    )
    db.add(new_project)
    db.flush()
    creator_member = ProjectMember(
        project_id=new_project.id, 
        user_id=current_user.id,
        background=data.background
    )
    db.add(creator_member)
    db.commit()
    db.refresh(new_project)
    return new_project


def _ensure_project_access(project_id: UUID, db: Session, current_user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
        )
        .first()
    )

    if project.created_by != current_user.id and not is_member:
        raise HTTPException(status_code=403, detail="Access denied to this project")

    return project


def get_project_documents(project_id: UUID, db: Session, current_user: User):
    _ensure_project_access(project_id, db, current_user)

    documents = db.query(Document).filter(Document.project_id == project_id).all()
    return [
        {"id": str(d.id), "title": d.title, "created_at": d.created_at}
        for d in documents
    ]


def get_project_tasks(project_id: UUID, db: Session, current_user: User):
    _ensure_project_access(project_id, db, current_user)

    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .order_by(Task.created_at.desc())
        .all()
    )
    for task in tasks:
        if task.assignee and task.assignee.user:
            task.assignee_name = task.assignee.user.name or task.assignee.user.email
    return tasks


def _normalize_task_complexity(value: str | None) -> TaskComplexity:
    normalized = (value or "medium").strip().lower()
    if normalized == "critical":
        return TaskComplexity.HIGH
    try:
        return TaskComplexity(normalized)
    except ValueError:
        return TaskComplexity.MEDIUM


def _normalize_task_status(value: str | None) -> TaskStatus:
    normalized = (value or TaskStatus.TODO.value).strip().lower()
    try:
        return TaskStatus(normalized)
    except ValueError:
        return TaskStatus.TODO


def create_project_task(
    project_id: UUID, data: schemas.TaskCreate, db: Session, current_user: User
):
    project = _ensure_project_access(project_id, db, current_user)

    task_kwargs = dict(
        title=data.title,
        description=data.description,
        complexity=_normalize_task_complexity(data.complexity),
        category=TaskCategory.BACKEND,
        priority=TaskPriority.MEDIUM,
        project_id=project.id,
        project_member_id=data.project_member_id,
        status=TaskStatus.TODO,
        ai_generated=False,
    )
    if "deadline" in Task.__table__.columns.keys():
        task_kwargs["deadline"] = data.deadline

    new_task = Task(**task_kwargs)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Enrich with assignee_name for the immediate response
    if new_task.assignee and new_task.assignee.user:
        new_task.assignee_name = new_task.assignee.user.name or new_task.assignee.user.email
        
    return new_task


def add_project_member(
    project_id: UUID,
    data: schemas.AddMemberRequest,
    background_tasks: BackgroundTasks,
    db: Session,
    current_user: User,
):
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the project owner can add members"
        )

    target_email = data.email.lower().strip()
    target_user = db.query(User).filter(User.email == target_email).first()

    if not target_user:
        target_user = User(
            name=target_email.split("@")[0],
            email=target_email,
            password_hash=None,
        )
        db.add(target_user)
        db.flush()
    else:
        existing_member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == target_user.id,
            )
            .first()
        )
        if existing_member or target_user.id == project.created_by:
            raise HTTPException(
                status_code=400, detail="User is already a member of this project"
            )

    new_member = ProjectMember(project_id=project_id, user_id=target_user.id)
    db.add(new_member)
    db.commit()

    background_tasks.add_task(
        utils.send_invitation_email,
        to_email=target_email,
        project_name=project.name,
        inviter_name=current_user.name,
    )

    return {"message": f"User {target_email} added to project."}


def get_project_members(project_id: UUID, db: Session, current_user: User):
    _ensure_project_access(project_id, db, current_user)
    
    members = (
        db.query(User, ProjectMember.id.label("project_member_id"))
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .filter(ProjectMember.project_id == project_id)
        .all()
    )
    
    result = []
    for user_obj, pm_id in members:
        result.append({
            "id": pm_id,
            "user_id": user_obj.id,
            "name": user_obj.name,
            "email": user_obj.email,
            "status": "Active" if user_obj.password_hash else "Pending"
        })
    return result


def update_project_task(
    project_id: UUID, task_id: UUID, data: schemas.TaskUpdate, db: Session, current_user: User
):
    _ensure_project_access(project_id, db, current_user)
    
    task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "complexity":
            task.complexity = _normalize_task_complexity(value)
            continue
        if field == "status":
            task.status = _normalize_task_status(value)
            continue
        if field == "deadline" and "deadline" not in Task.__table__.columns.keys():
            continue
        if hasattr(task, field):
            setattr(task, field, value)
        
    db.commit()
    db.refresh(task)
    
    if task.assignee and task.assignee.user:
        task.assignee_name = task.assignee.user.name or task.assignee.user.email
    else:
        task.assignee_name = None
        
    return task


def delete_project(project_id: UUID, db: Session, current_user: User):
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the project owner can delete the project"
        )

    project.deleted_at = func.now()
    db.commit()
    return {"message": "Project deleted successfully"}

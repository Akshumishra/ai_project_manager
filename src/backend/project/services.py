from sqlalchemy.orm import Session
from fastapi import HTTPException, BackgroundTasks
from uuid import UUID
from . import schemas, utils
from src.backend.model.project import Project, ProjectMember
from src.backend.model.document import Document
from src.backend.model.user import User


def get_projects(db: Session, current_user: User):
    member_project_ids = (
        db.query(ProjectMember.project_id)
        .filter(ProjectMember.user_id == current_user.id)
        .all()
    )
    member_project_ids = [r[0] for r in member_project_ids]
    return db.query(Project).filter(Project.id.in_(member_project_ids)).all()


def create_project(data: schemas.ProjectCreateRequest, db: Session, current_user: User):
    new_project = Project(
        name=data.name, description=data.description, created_by=current_user.id
    )
    db.add(new_project)
    db.flush()
    creator_member = ProjectMember(project_id=new_project.id, user_id=current_user.id)
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


def _verify_project_ownership(project_id: UUID, db: Session, user_id: UUID) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.created_by != user_id:
        raise HTTPException(
            status_code=403, detail="Only the project owner can add members"
        )
    return project


def _get_or_create_user_by_email(email: str, db: Session) -> User:
    target_email = email.lower().strip()
    target_user = db.query(User).filter(User.email == target_email).first()

    if not target_user:
        target_user = User(
            name=target_email.split("@")[0],
            email=target_email,
            password_hash=None,
        )
        db.add(target_user)
        db.flush()
    return target_user


def _check_if_member_exists(project_id: UUID, user_id: UUID, creator_id: UUID, db: Session):
    existing_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        .first()
    )
    if existing_member or user_id == creator_id:
        raise HTTPException(
            status_code=400, detail="User is already a member of this project"
        )


def add_project_member(
    project_id: UUID,
    data: schemas.AddMemberRequest,
    background_tasks: BackgroundTasks,
    db: Session,
    current_user: User,
):
    project = _verify_project_ownership(project_id, db, current_user.id)
    target_user = _get_or_create_user_by_email(data.email, db)
    _check_if_member_exists(project_id, target_user.id, project.created_by, db)

    new_member = ProjectMember(project_id=project_id, user_id=target_user.id)
    db.add(new_member)
    db.commit()

    background_tasks.add_task(
        utils.send_invitation_email,
        to_email=target_user.email,
        project_name=project.name,
        inviter_name=current_user.name,
    )

    return {"message": f"User {target_user.email} added to project."}

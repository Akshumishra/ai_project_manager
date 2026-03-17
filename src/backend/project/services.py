from sqlalchemy.orm import Session
from fastapi import HTTPException, BackgroundTasks
from uuid import UUID
import datetime
from . import schemas, utils
from src.backend.model.project import Project, ProjectMember
from src.backend.model.document import Document
from src.backend.model.user import User

def get_projects(db: Session, current_user: User):
    try:
        # User's own projects
        own_projects = (
            db.query(Project)
            .filter(Project.created_by == current_user.id, Project.deleted_at.is_(None))
            .all()
        )

        # Projects where user is a member
        member_project_ids = (
            db.query(ProjectMember.project_id)
            .filter(ProjectMember.user_id == current_user.id, ProjectMember.deleted_at.is_(None))
            .all()
        )
        member_project_ids = [pid for (pid,) in member_project_ids]

        member_projects = (
            db.query(Project)
            .filter(Project.id.in_(member_project_ids), Project.deleted_at.is_(None))
            .all()
        )

        # Merge and remove duplicates
        all_projects = list({p.id: p for p in (own_projects + member_projects)}.values())
        return all_projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")

def create_project(data: schemas.ProjectCreateRequest, db: Session, current_user: User):
    try:
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

def get_project(project_id: UUID, db: Session, current_user: User):
    try:
        project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        is_member = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id, ProjectMember.deleted_at.is_(None))
            .first()
        )

        if project.created_by != current_user.id and not is_member:
            raise HTTPException(status_code=403, detail="No access to this project")

        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project detail: {str(e)}")

def get_project_documents(project_id: UUID, db: Session, current_user: User):
    try:
        # Use the new get_project function for access control
        project = get_project(project_id, db, current_user)

        documents = db.query(Document).filter(Document.project_id == project.id, Document.deleted_at.is_(None)).all()
        return [
            {"id": str(d.id), "title": d.title, "created_at": d.created_at}
            for d in documents
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project documents: {str(e)}")

def update_project(
    project_id: UUID, data: schemas.ProjectUpdateRequest, db: Session, current_user: User
):
    try:
        project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project.created_by != current_user.id:
            raise HTTPException(
                status_code=403, detail="Only the creator can update the project"
            )

        if data.name:
            project.name = data.name
        if data.description:
            project.description = data.description
        if data.status:
            project.status = data.status

        db.commit()
        db.refresh(project)
        return project
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")

def delete_project(project_id: UUID, db: Session, current_user: User):
    try:
        project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project.created_by != current_user.id:
            raise HTTPException(
                status_code=403, detail="Only the creator can delete the project"
            )

        # Soft delete the project
        project.deleted_at = datetime.datetime.utcnow()
        db.commit()
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")

def _verify_project_ownership(project_id: UUID, db: Session, user_id: UUID) -> Project:
    try:
        project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project.created_by != user_id:
            raise HTTPException(
                status_code=403, detail="Only the project owner can add members"
            )
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify project ownership: {str(e)}")

def _get_or_create_user_by_email(email: str, db: Session) -> User:
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get/create user: {str(e)}")

def _check_if_member_exists(project_id: UUID, user_id: UUID, creator_id: UUID, db: Session):
    try:
        existing_member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.deleted_at.is_(None)
            )
            .first()
        )
        if existing_member or user_id == creator_id:
            raise HTTPException(
                status_code=400, detail="User is already a member of this project"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking member existence: {str(e)}")

def add_project_member(
    project_id: UUID,
    data: schemas.AddMemberRequest,
    background_tasks: BackgroundTasks,
    db: Session,
    current_user: User,
):
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add project member: {str(e)}")

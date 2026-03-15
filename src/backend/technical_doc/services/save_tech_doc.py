from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from uuid import UUID

from src.backend.model.document import Document
from src.backend.model.project import Project
from src.backend.model.user import User
from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.technical_doc.constants import TechDocAgentConstants
from src.backend.collaborative_document import document_service as doc_services, schemas as doc_schemas

def save_technical_spec_in_db(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    markdown_content: str,
    background_tasks: BackgroundTasks = None
):
    """
    Standardized service to save technical specification into the database
    using the collaborative document block-based system.
    """
    try:
        project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
        if not project_title:
            return False, "Project not found"
            
        document_title = f"{project_title} - {TechDocAgentConstants.TECH_DOC_LABEL}"
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            return False, "User not found"

        existing_docs = db.query(Document).filter(
            Document.project_id == project_id,
            Document.title == document_title
        ).all()
        for d in existing_docs:
            db.delete(d)
        db.flush()

        doc_services.save_document(
            data=doc_schemas.DocumentCreate(title=document_title, project_id=project_id),
            markdown_content=markdown_content,
            db=db,
            current_user=current_user
        )

        set_workflow_status(db, project_id, TechDocAgentConstants.WORKFLOW_NAME, "completed")
        db.commit()

        if background_tasks:
            from src.backend.task_creator.task_creator_services import generate_and_save_tasks
            background_tasks.add_task(generate_and_save_tasks, db, project_id)

        return True, "Technical specification saved successfully."
    except Exception as e:
        db.rollback()
        return False, str(e)

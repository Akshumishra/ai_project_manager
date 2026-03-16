import logging
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from uuid import UUID

from src.backend.model.document import Document
from src.backend.model.project import Project
from src.backend.model.user import User
from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.technical_doc.constants import TechDocAgentConstants
from src.backend.collaborative_document import document_service as doc_services, schemas as doc_schemas

logger = logging.getLogger(__name__)

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
        logger.info(f"Saving tech doc for project: {project_id}, user: {user_id}")
        project_title = db.query(Project.name).filter(
            Project.id == project_id, 
            Project.deleted_at.is_(None)
        ).scalar()
        
        if not project_title:
            logger.error(f"Project not found or deleted: {project_id}")
            return {"success": False, "message": "Project not found"}
            
        document_title = f"{project_title} - {TechDocAgentConstants.TECH_DOC_LABEL}"
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            logger.error(f"User not found: {user_id}")
            return {"success": False, "message": "User not found"}

        existing_docs = db.query(Document).filter(
            Document.project_id == project_id,
            Document.title.ilike("%Technical%")
        ).all()

        existing_doc = existing_docs[0] if existing_docs else None
        for d in existing_docs[1:]:
            db.delete(d)
        db.flush()

        if existing_doc:
            logger.info(f"Updating existing tech doc: {existing_doc.id}")
            existing_doc.title = document_title
            doc_services.utils.sync_blocks_from_text(existing_doc.id, markdown_content, db)
        else:
            logger.info("Creating new tech doc")
            doc_services.save_document(
                data=doc_schemas.DocumentCreate(title=document_title, project_id=project_id),
                markdown_content=markdown_content,
                db=db,
                current_user=current_user,
                auto_commit=False,
            )

        set_workflow_status(
            db,
            project_id,
            TechDocAgentConstants.WORKFLOW_NAME,
            "completed",
            auto_commit=False,
        )
        db.commit()

        if background_tasks:
            logger.info("Adding task generation to background tasks")
            from src.backend.task_creator.task_creator_services import generate_and_save_tasks
            background_tasks.add_task(generate_and_save_tasks, project_id)

        return {"success": True, "message": "Technical specification saved successfully."}
    except Exception as e:
        db.rollback()
        import traceback
        error_msg = f"Save failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg}

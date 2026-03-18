import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from uuid import UUID

from src.backend.model.document import Document
from src.backend.model.project import Project
from src.backend.model.user import User
from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.technical_doc.constants import TechDocAgentConstants
from src.backend.technical_doc.doc_sync import sync_blocks_from_text

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
        # Soft-delete any duplicate docs (keep the first one)
        for d in existing_docs[1:]:
            d.deleted_at = datetime.now(timezone.utc)
        db.flush()

        if existing_doc:
            logger.info(f"Updating existing tech doc: {existing_doc.id}")
            existing_doc.title = document_title
            sync_blocks_from_text(existing_doc.id, markdown_content, db)
            doc_id = existing_doc.id
        else:
            logger.info("Creating new tech doc")
            new_doc = Document(
                title=document_title,
                project_id=project_id,
                created_by=user_id
            )
            db.add(new_doc)
            db.flush()
            sync_blocks_from_text(new_doc.id, markdown_content, db)
            doc_id = new_doc.id

        db.flush()

        set_workflow_status(
            db,
            project_id,
            TechDocAgentConstants.WORKFLOW_NAME,
            "completed"
        )
        db.commit()

        if background_tasks:
            logger.info("Adding task generation to background tasks")
            from src.backend.task_creator.task_creator_service import generate_and_save_tasks
            background_tasks.add_task(generate_and_save_tasks, project_id, user_id)

        return {
            "success": True, 
            "message": "Technical specification saved successfully.",
            "document_id": str(doc_id)
        }
    except Exception as e:
        db.rollback()
        import traceback
        error_msg = f"Save failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg}

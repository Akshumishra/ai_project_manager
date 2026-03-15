from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.model.document import Document
from src.backend.model.project import Project
from src.backend.model.user import User
from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.requirement_gather.constants import RequirementAgentConstants
from src.backend.collaborative_document import services as doc_services, schemas as doc_schemas

def save_requirement_spec_in_db(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    markdown_content: str,
):
    """
    Main service to orchestrate saving the requirement specification into the database
    using the collaborative document services.
    """
    try:
        project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
        document_title = f"{project_title} - {RequirementAgentConstants.REQ_DOC_LABEL}"
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            return False, "User not found"

        doc_services.create_document(
            data=doc_schemas.DocumentCreate(title=document_title, project_id=project_id),
            markdown_content=markdown_content,
            db=db,
            current_user=current_user
        )

        set_workflow_status(db, project_id, RequirementAgentConstants.WORKFLOW_NAME, "completed")
        db.commit()

        return True, "Requirement specification saved successfully."
    except Exception as e:
        db.rollback()
        return False, str(e)

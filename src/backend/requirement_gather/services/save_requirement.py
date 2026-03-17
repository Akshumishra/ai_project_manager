from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.model.document import Document
from src.backend.model.project import Project
from src.backend.model.user import User
from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.requirement_gather.constants import RequirementAgentConstants
from src.backend.requirement_gather.utils.doc_utils import sync_blocks_from_text, save_document

def save_requirement_spec_document(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    markdown_content: str | None = None,
    problem_the_project_solves: str | None = None,
    target_users: str | None = None,
    project_goal: str | None = None,
    key_system_capabilities: str | None = None,
    expected_outcome: str | None = None,
    major_constraints: str | None = None,
    additional_notes: str | None = None,
):
    """
    Main service to orchestrate saving the requirement specification into the database
    using local document utilities to avoid external service dependencies.
    """
    try:
        project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
        if not markdown_content:
            markdown_content = f"# {project_title}\n\n## Requirement Specification\n\n"
            if problem_the_project_solves:
                markdown_content += f"### Problem\n{problem_the_project_solves}\n\n"
            if target_users:
                markdown_content += f"### Users\n{target_users}\n\n"
            if project_goal:
                markdown_content += f"### Goal\n{project_goal}\n\n"
            if key_system_capabilities:
                markdown_content += f"### Core Features\n{key_system_capabilities}\n\n"
            if expected_outcome:
                markdown_content += f"### Expected Outcome\n{expected_outcome}\n\n"
            if major_constraints or additional_notes:
                markdown_content += f"### Constraints / Notes\n{major_constraints or ''}\n{additional_notes or ''}\n\n"

        document_title = f"{project_title} - {RequirementAgentConstants.REQ_DOC_LABEL}"
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            return False, "User not found"

        existing_doc = (
            db.query(Document)
            .filter(
                Document.project_id == project_id,
                Document.title.like(f"%{RequirementAgentConstants.REQ_DOC_LABEL}%")
            )
            .first()
        )

        if existing_doc:
            sync_blocks_from_text(existing_doc.id, markdown_content, db)
            doc_id = str(existing_doc.id)
        else:
            doc_info = save_document(
                title=document_title,
                project_id=project_id,
                created_by=user_id,
                markdown_content=markdown_content,
                db=db
            )
            doc_id = doc_info["document_id"]

        db.commit()
        return True, {"message": "Requirement specification saved successfully.", "document_id": doc_id}
    except Exception as e:
        db.rollback()
        return False, str(e)

def complete_requirement_step(db: Session, project_id: UUID):
    """
    Updates the workflow status to completed for the requirement step.
    """
    try:
        set_workflow_status(db, project_id, RequirementAgentConstants.WORKFLOW_NAME, "completed")
        db.commit()
        return True, "Requirement step marked as completed."
    except Exception as e:
        db.rollback()
        return False, str(e)

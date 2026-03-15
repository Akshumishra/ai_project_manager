from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.model.document import Document
from src.backend.model.project import Project
from src.backend.model.user import User
from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.requirement_gather.constants import RequirementAgentConstants
from src.backend.collaborative_document import document_service as doc_services, schemas as doc_schemas

def save_requirement_spec_in_db(
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
    using the collaborative document services.
    """
    if not markdown_content:
        markdown_content = f"# Requirement Specification\n\n"
        if problem_the_project_solves:
            markdown_content += f"## Problem\n{problem_the_project_solves}\n\n"
        if target_users:
            markdown_content += f"## Users\n{target_users}\n\n"
        if project_goal:
            markdown_content += f"## Goal\n{project_goal}\n\n"
        if key_system_capabilities:
            markdown_content += f"## Core Features\n{key_system_capabilities}\n\n"
        if expected_outcome:
            markdown_content += f"## Expected Outcome\n{expected_outcome}\n\n"
        if major_constraints or additional_notes:
            markdown_content += f"## Constraints / Notes\n{major_constraints or ''}\n{additional_notes or ''}\n\n"

    try:
        project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
        document_title = f"{project_title} - {RequirementAgentConstants.REQ_DOC_LABEL}"
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            return False, "User not found"

        doc_services.save_document(
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

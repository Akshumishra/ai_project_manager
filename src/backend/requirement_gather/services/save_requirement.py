from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Tuple
from src.backend.model.document import Document, DocumentBlock
from src.backend.model.project import Project, ProjectWorkflowStatus
from src.backend.model.user import User
from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.requirement_gather.constants import RequirementAgentConstants
from src.backend.collaborative_document import services as doc_services, schemas as doc_schemas

def save_requirement_spec_in_db(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    problem_the_project_solves: str,
    target_users: str,
    project_goal: str,
    key_system_capabilities: str,
    expected_outcome: str,
    major_constraints: str,
    additional_notes: str,
):
    """
    Main service to orchestrate saving the requirement specification into the database
    using the collaborative document services.
    """
    try:
        project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
        document_title = f"{project_title} - {RequirementAgentConstants.REQ_DOC_LABEL}"
        
        # 1. Cleanup old requirement docs
        old_docs = (
            db.query(Document)
            .filter(
                Document.project_id == project_id,
                Document.title.in_([
                    document_title,
                    f"{project_title} - Requirement",
                    f"{project_title} - Requirements",
                    f"{project_title} - Requirement Specification",
                    "{project_title} - Requirement Specification",
                    "Requirement Specification",
                ]),
            )
            .all()
        )
        for old_doc in old_docs:
            db.delete(old_doc)
        if old_docs:
            db.flush()

        # 2. Prepare user object
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            return False, "User not found"

        # 3. Use collaborative document services for creation and block population
        doc_create_data = doc_schemas.DocumentCreate(
            title=document_title,
            project_id=project_id
        )

        blocks_payload = [
            doc_schemas.BlockCreate(content=f"## Problem the Project Solves\n{problem_the_project_solves}"),
            doc_schemas.BlockCreate(content=f"## Target Users\n{target_users}"),
            doc_schemas.BlockCreate(content=f"## Project Goal\n{project_goal}"),
            doc_schemas.BlockCreate(content=f"## Key System Capabilities\n{key_system_capabilities}"),
            doc_schemas.BlockCreate(content=f"## Expected Outcome\n{expected_outcome}"),
            doc_schemas.BlockCreate(content=f"## Major Constraints\n{major_constraints}"),
            doc_schemas.BlockCreate(content=f"## Additional Notes\n{additional_notes}")
        ]

        doc_services.create_document_with_blocks(
            data=doc_create_data,
            blocks_data=blocks_payload,
            db=db,
            current_user=current_user
        )

        # 4. Update workflow status
        set_workflow_status(db, project_id, RequirementAgentConstants.WORKFLOW_NAME, "completed")
        db.commit()

        return True, "Requirement specification saved successfully."
    except Exception as e:
        db.rollback()
        return False, str(e)

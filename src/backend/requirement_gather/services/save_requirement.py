from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import re

from src.backend.model.document import Document
from src.backend.model.project import Project
from src.backend.model.user import User
from src.backend.model.requirement_chat import RequirementChat
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
    Main service to orchestrate saving the requirement specification into the database.
    On first save: creates the document and all its blocks.
    On subsequent saves: updates blocks.
    Returns a success dictionary for the AI to confirm the action.
    """
    try:
        project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
        if not project_title:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        # Build markdown from individual fields if not provided directly
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        existing_doc = (
            db.query(Document)
            .filter(
                Document.project_id == project_id,
                Document.title.ilike(f"%{RequirementAgentConstants.REQ_DOC_LABEL}%")
            )
            .first()
        )

        if existing_doc:
            # Update: only changed blocks are modified (smart diff)
            sync_blocks_from_text(existing_doc.id, markdown_content, db)
            doc_id = str(existing_doc.id)
        else:
            # First save: create document + all blocks
            doc_info = save_document(
                title=document_title,
                project_id=project_id,
                created_by=user_id,
                markdown_content=markdown_content,
                db=db
            )
            doc_id = str(doc_info["document_id"])

        db.commit()
        
        return {
            "status": "success", 
            "message": "Requirement specification saved successfully.",
            "document_id": doc_id
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save requirement: {str(e)}"
        )


def extract_latest_spec_from_history(db: Session, project_id: UUID) -> str | None:
    """
    Finds the latest assistant message in history that contains a valid specification.
    """
    history = (
        db.query(RequirementChat)
        .filter(RequirementChat.project_id == project_id, RequirementChat.role == "assistant")
        .order_by(RequirementChat.created_at.desc())
        .all()
    )

    marker_regex = r"^[—-]{1,5}\s*Requirement Specification\s*$(.*)"

    for msg in history:
        content = msg.content or ""
        # 1. Look for marker
        match = re.search(marker_regex, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()

        # 2. Look for heading fallback
        if "# " in content:
            parts = content.split("# ", 1)
            if len(parts) > 1:
                potential = "# " + parts[1].strip()
                if len(potential) > 200:
                    return potential

    return None


def complete_requirement_step(db: Session, project_id: UUID):
    """
    Updates the workflow status to completed for the requirement step.
    Also ensures the latest draft is saved if not already present.
    """
    try:
        set_workflow_status(db, project_id, RequirementAgentConstants.WORKFLOW_NAME, "completed")
        db.commit()
        return {"status": "success", "message": "Requirement step marked as completed."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete requirement step: {str(e)}"
        )

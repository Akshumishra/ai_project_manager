from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.model.document import Document, DocumentBlock
from src.backend.model.project import Project, ProjectWorkflowStatus


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
    Service to save the requirement specification into the database.
    """
    try:
        project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
        document_title = f"{project_title} - Requirement"
        old_docs = (
            db.query(Document)
            .filter(
                Document.project_id == project_id,
                Document.title.in_(
                    [
                        document_title,
                        f"{project_title} - Requirement Specification",
                        "{project_title} - Requirement Specification",
                        "Requirement Specification",
                    ]
                ),
            )
            .all()
        )

        for old_doc in old_docs:
            db.delete(old_doc)
        if old_docs:
            db.flush()

        new_doc = Document(
            project_id=project_id,
            title=document_title,
            created_by=user_id
        )
        db.add(new_doc)
        db.flush()

        blocks_data = [
            ("1000", "paragraph", f"Problem the Project Solves\n{problem_the_project_solves}"),
            ("2000", "paragraph", f"Target Users\n{target_users}"),
            ("3000", "paragraph", f"Project Goal\n{project_goal}"),
            ("4000", "paragraph", f"Key System Capabilities\n{key_system_capabilities}"),
            ("5000", "paragraph", f"Expected Outcome\n{expected_outcome}"),
            ("6000", "paragraph", f"Major Constraints\n{major_constraints}"),
            ("7000", "paragraph", f"Additional Notes\n{additional_notes}")
        ]

        for pos_key, type_val, content in blocks_data:
            block = DocumentBlock(
                doc_id=new_doc.id,
                content=content,
                position_key=pos_key,
                type=type_val,
                last_edited_by=user_id
            )
            db.add(block)

        # Update Workflow Status
        workflow_status = db.query(ProjectWorkflowStatus).filter(
            ProjectWorkflowStatus.project_id == project_id,
            ProjectWorkflowStatus.workflow_name == "requirement_gathering"
        ).first()

        if workflow_status:
            workflow_status.status = "completed"
        else:
            workflow_status = ProjectWorkflowStatus(
                project_id=project_id,
                workflow_name="requirement_gathering",
                status="completed"
            )
            db.add(workflow_status)

        db.commit()
        return True, "Requirement specification saved successfully."
    except Exception as e:
        db.rollback()
        return False, str(e)

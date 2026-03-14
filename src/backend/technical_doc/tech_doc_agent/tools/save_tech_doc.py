from langchain_core.tools import tool
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.technical_doc.document_sections import (
    build_project_document_title,
    save_markdown_as_section_blocks,
)

def make_save_tech_doc_tool(user_id: UUID, project_id: UUID):
    @tool
    def save_technical_document(document_markdown: str):
        """
        Use this tool ONLY when the user explicitly confirms and approves the final technical document.
        This saves the technical document definitively to the database as discrete blocks.
        """
        db: Session = SessionLocal()
        try:
            tech_doc_title = build_project_document_title(db, project_id, "Technical")
            doc_id = save_markdown_as_section_blocks(
                db=db,
                user_id=user_id,
                project_id=project_id,
                document_title=tech_doc_title,
                document_markdown=document_markdown,
                legacy_titles=[
                    "{project_title} - Technical Specification",
                    "Technical Specification",
                ],
            )

            from src.backend.model.project import ProjectWorkflowStatus
            workflow_status = db.query(ProjectWorkflowStatus).filter(
                ProjectWorkflowStatus.project_id == project_id,
                ProjectWorkflowStatus.workflow_name == "tech_doc_gathering"
            ).first()

            if workflow_status:
                workflow_status.status = "completed"
            else:
                workflow_status = ProjectWorkflowStatus(
                    project_id=project_id,
                    workflow_name="tech_doc_gathering",
                    status="completed"
                )
                db.add(workflow_status)
            
            db.commit()
            return f"Success! Document ID {doc_id} saved to database."
        except Exception as exc:
            return f"Error saving document: {str(exc)}"
        finally:
            db.close()
    
    return save_technical_document

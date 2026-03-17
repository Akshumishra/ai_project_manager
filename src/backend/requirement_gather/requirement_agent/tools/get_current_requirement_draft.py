from langchain_core.tools import tool
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.model.document import Document, DocumentBlock
from src.backend.requirement_gather.constants import RequirementAgentConstants

def get_requirement_draft_tool(project_id: UUID):

    @tool
    def get_current_requirement_draft():
        """
        Retrieves the current saved draft of the Requirement Specification for this project.
        Use this to see what has been already documented and saved.
        """
        db: Session = SessionLocal()
        try:
            doc = db.query(Document).filter(
                Document.project_id == project_id,
                Document.title.contains(RequirementAgentConstants.REQ_DOC_LABEL)
            ).first()

            if not doc:
                return "No requirement document draft found yet."

            blocks = db.query(DocumentBlock).filter(
                DocumentBlock.doc_id == doc.id
            ).order_by(DocumentBlock.position_key).all()

            if not blocks:
                return "Requirement document exists but has no content yet."

            content = "\n\n".join([b.content for b in blocks if b.content])
            return content

        except Exception as e:
            return f"Error retrieving draft: {str(e)}"
        finally:
            db.close()

    return get_current_requirement_draft

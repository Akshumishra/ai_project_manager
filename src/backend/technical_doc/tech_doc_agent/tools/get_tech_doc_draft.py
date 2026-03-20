from langchain_core.tools import tool
from uuid import UUID

from src.backend.db.database import get_session_local
from src.backend.model.document import DocumentType
from src.backend.utils.doc_utils import get_document_content

def make_get_tech_doc_draft_tool(project_id: UUID):

    @tool
    def get_current_technical_doc_draft():
        """
        Retrieves the current saved draft of the Technical Specification for this project.
        Use this to see what has been already documented and saved.
        """
        db = get_session_local()()
        try:
            content = get_document_content(db, project_id, DocumentType.TECHNICAL)
            if not content:
                return "No technical document draft found yet or it has no content."
            return content

        except Exception as e:
            return f"Error retrieving draft: {str(e)}"
        finally:
            db.close()

    return get_current_technical_doc_draft

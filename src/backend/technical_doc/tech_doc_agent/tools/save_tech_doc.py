from langchain_core.tools import tool
from uuid import UUID
from src.backend.db.database import get_session_local
from src.backend.model.document import DocumentType
from src.backend.utils.doc_utils import upsert_document
from src.backend.technical_doc.constants import TechDocAgentConstants

def make_save_tech_doc_tool(user_id: UUID, project_id: UUID):
    @tool
    def save_technical_specification(document_markdown: str):
        """
        Use this tool to save or update the Technical Specification document in markdown format. 
        The system will automatically organize it into documents and blocks in the database.
        Call this WHENEVER you want to sync the latest version to the user's screen.
        """
        db = get_session_local()()
        try:
            result = upsert_document(
                db=db,
                user_id=user_id,
                project_id=project_id,
                document_type=DocumentType.TECHNICAL,
                markdown_content=document_markdown,
                title_label=TechDocAgentConstants.TECH_DOC_LABEL
            )
            db.commit()
            return f"Technical specification saved successfully. Doc ID: {result.get('document_id')}"
        except Exception as e:
            db.rollback()
            return f"Failed to save specification: {str(e)}"
        finally:
            db.close()

    return save_technical_specification

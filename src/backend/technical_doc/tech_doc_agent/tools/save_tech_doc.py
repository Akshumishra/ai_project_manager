from langchain_core.tools import tool
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_session_local
from src.backend.technical_doc.document_sections import (
    build_project_document_title,
)

def make_save_tech_doc_tool(user_id: UUID, project_id: UUID):
    @tool
    def save_technical_document(document_markdown: str):
        """
        Use this tool ONLY when the user explicitly confirms and approves the final technical document.
        This saves the technical document definitively to the database as discrete blocks.
        """
        db: Session = get_session_local()()
        try:
            from src.backend.technical_doc.services.save_tech_doc import save_technical_spec_in_db
            
            result = save_technical_spec_in_db(
                db=db,
                user_id=user_id,
                project_id=project_id,
                markdown_content=document_markdown
            )

            if result.get("success"):
                return f"Success! {result.get('message')}"
            else:
                return f"Error: {result.get('message')}"
        except Exception as exc:
            return f"Error saving document: {str(exc)}"
        finally:
            db.close()
    
    return save_technical_document

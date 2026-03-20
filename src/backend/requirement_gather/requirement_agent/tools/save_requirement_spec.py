from langchain_core.tools import tool
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_session_local
from src.backend.model.document import DocumentType
from src.backend.utils.doc_utils import upsert_document
from src.backend.requirement_gather.constants import RequirementAgentConstants


def save_requirement_spec_tool(user_id: UUID, project_id: UUID):

    @tool
    def save_requirement_specification(
        markdown_content: str,
    ):
        """
        Save the final requirement specification in markdown format. 
        The system will automatically organize it into documents and blocks.
        """
        db = get_session_local()()

        try:
            result = upsert_document(
                db=db,
                project_id=project_id,
                user_id=user_id,
                document_type=DocumentType.REQUIREMENT,
                markdown_content=markdown_content,
                title_label=RequirementAgentConstants.REQ_DOC_LABEL
            )
            db.commit()

            if result.get("status") == "success":
                return f"Requirement specification saved successfully. Document ID: {result.get('document_id', 'N/A')}"
            else:
                return f"Save failed: {result.get('message', 'Unknown error')}"

        except Exception as e:
            return f"Save failed: {str(e)}"

        finally:
            db.close()

    return save_requirement_specification
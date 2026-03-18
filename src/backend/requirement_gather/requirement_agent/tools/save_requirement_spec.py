from langchain_core.tools import tool
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_session_local
from src.backend.requirement_gather.services.save_requirement import save_requirement_spec_document


def save_requirement_spec_tool(user_id: UUID, project_id: UUID):

    @tool
    def save_requirement_specification(
        markdown_content: str,
    ):
        """
        Save the final requirement specification in markdown format. 
        The system will automatically organize it into documents and blocks.
        """
        factory = get_session_local()
        db: Session = factory()

        try:
            success, message = save_requirement_spec_document(
                db=db,
                user_id=user_id,
                project_id=project_id,
                markdown_content=markdown_content
            )

            if success:
                return {
                    "status": "success",
                    "result": message
                }
            else:
                return {
                    "status": "error",
                    "message": message
                }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

        finally:
            db.close()

    return save_requirement_specification
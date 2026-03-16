from langchain_core.tools import tool
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.requirement_gather.services.save_requirement import save_requirement_spec_in_db


def make_save_requirement_spec_tool(user_id: UUID, project_id: UUID):

    @tool
    def save_requirement_specification(
        markdown_content: str,
    ):
        """
        Save the final requirement specification in markdown format. 
        The system will automatically organize it into documents and blocks.
        """
        db: Session = SessionLocal()

        try:
            success, message = save_requirement_spec_in_db(
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
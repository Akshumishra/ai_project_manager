from langchain_core.tools import tool
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.requirement_gather.services.save_requirement import save_requirement_spec_in_db


def make_save_requirement_spec_tool(user_id: UUID, project_id: UUID):

    @tool
    def save_requirement_spec(
        problem_the_project_solves: str,
        target_users: str,
        project_goal: str,
        key_system_capabilities: str,
        expected_outcome: str,
        major_constraints: str,
        additional_notes: str,
    ):
        """
        Save the requirement specification for the project into the documents table as discrete blocks.
        """

        db: Session = SessionLocal()

        try:
            success, message = save_requirement_spec_in_db(
                db=db,
                user_id=user_id,
                project_id=project_id,
                problem_the_project_solves=problem_the_project_solves,
                target_users=target_users,
                project_goal=project_goal,
                key_system_capabilities=key_system_capabilities,
                expected_outcome=expected_outcome,
                major_constraints=major_constraints,
                additional_notes=additional_notes
            )

            if success:
                return {
                    "status": "success",
                    "message": message
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

    return save_requirement_spec
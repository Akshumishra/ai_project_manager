import logging
from uuid import UUID

from src.backend.db.database import SessionLocal
from src.backend.task_creator.task_creator_agent.agent import TaskCreatorAgent
from src.backend.technical_doc.services.tech_doc_service import (
    fetch_requirement_specification_text,
    fetch_technical_specification_text,
)

from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.task_creator.constants import TaskCreatorConstants as TaskConstants
from src.backend.task_creator.task_creator_agent.prompt import user_prompt

logger = logging.getLogger(__name__)


def generate_and_save_tasks(project_id: UUID, user_id: UUID):
    """Generate and persist tasks for a project based on requirement + technical docs."""

    db = SessionLocal()
    try:
        set_workflow_status(db, project_id, "task_generation", "thinking")
        db.commit()
        # Fetch the current requirement and technical spec text.
        requirement_text = fetch_requirement_specification_text(db, project_id)
        technical_text = fetch_technical_specification_text(db, project_id)

        # Build the message the agent will use to generate tasks using the template.
        formatted_user_prompt = user_prompt.format(
            requirement_document=requirement_text,
            technical_document=technical_text
        )

        agent = TaskCreatorAgent(user_id=user_id, project_id=project_id)
        response = agent.run([{"role": "user", "content": formatted_user_prompt}])

        # Log details for debugging
        logger.info(
            "Task generation complete for project %s (user: %s). tool_called=%s",
            project_id,
            user_id,
            response.get("tasks_saved", False),
        )

        return response

    except Exception as e:
        set_workflow_status(db, project_id, "task_generation", "failed")
        db.commit()
        logger.exception("Task generation failed for project %s: %s", project_id, str(e))
        return {"status": "error", "message": str(e)}

    finally:
        db.close()

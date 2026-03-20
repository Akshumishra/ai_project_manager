import logging
from uuid import UUID

from src.backend.db.database import get_session_local
from src.backend.task_creator.task_creator_agent.agent import TaskCreatorAgent
from src.backend.model.document import DocumentType
from src.backend.utils.doc_utils import get_document_content
from src.backend.model.project import WorkflowStatus
from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.task_creator.constants import TaskCreatorConstants as TaskConstants
from src.backend.task_creator.task_creator_agent.prompt import user_prompt

logger = logging.getLogger(__name__)


def generate_and_save_tasks(project_id: UUID, user_id: UUID):
    """Generate and persist tasks for a project based on requirement + technical docs."""

    db = get_session_local()()
    try:
        set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, WorkflowStatus.THINKING)
        
        # Fetch docs... (requirement + technical)
        requirement_text = get_document_content(db, project_id, DocumentType.REQUIREMENT)
        technical_text = get_document_content(db, project_id, DocumentType.TECHNICAL)

        if not requirement_text or requirement_text.strip().startswith("No Requirement"):
            logger.warning(f"Missing Requirements for project {project_id}.")
            set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, WorkflowStatus.IN_PROGRESS)
            return


        formatted_user_prompt = user_prompt.format(
            requirement_document=requirement_text,
            technical_document=technical_text
        )

        agent = TaskCreatorAgent(user_id=user_id, project_id=project_id)
        response = agent.run([{"role": "user", "content": formatted_user_prompt}])

        if response.get("tasks_saved"):
            logger.info("Task generation successful for project %s.", project_id)
            set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, WorkflowStatus.COMPLETED)
        else:
            logger.warning("TaskCreatorAgent failed to save tasks for project %s.", project_id)
            set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, WorkflowStatus.IN_PROGRESS)

        return response

    except Exception as e:
        logger.exception("Task generation failed for project %s: %s", project_id, str(e))
        set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, WorkflowStatus.IN_PROGRESS)
        return {"status": "error", "message": str(e)}

    finally:
        db.close()

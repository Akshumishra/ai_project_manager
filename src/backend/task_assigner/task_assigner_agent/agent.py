from src.backend.utils.agent_utils import create_agent, get_last_ai_content
from uuid import UUID
from typing import Any, Dict, List

from src.backend.task_assigner.task_assigner_agent.prompt import SYSTEM_PROMPT
from src.backend.task_assigner.constants import TaskAssignerConstants
from src.backend.task_assigner.task_assigner_agent.tools.get_unassigned_tasks import make_get_unassigned_tasks_tool
from src.backend.task_assigner.task_assigner_agent.tools.get_project_members import make_get_project_members_tool
from src.backend.task_assigner.task_assigner_agent.tools.assign_task import make_assign_task_tool
from src.backend.config import settings
import logging

logger = logging.getLogger(__name__)


class TaskAssignerAgent:
    def __init__(self, project_id: UUID):
        self.project_id = project_id
        self.agent = create_agent(
            model=TaskAssignerConstants.MODEL,
            temperature=TaskAssignerConstants.TEMPERATURE,
            tools=[
                make_get_unassigned_tasks_tool(project_id),
                make_get_project_members_tool(project_id),
                make_assign_task_tool()
            ],
            system_prompt=SYSTEM_PROMPT
        )

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        logger.info(f"Running TaskAssignerAgent for project {self.project_id}")
        try:
            response = self.agent.invoke({
                "messages": messages
            })
            response_messages = response["messages"]
            
            content = get_last_ai_content(response_messages)

            return {
                "content": content
            }
        except Exception as e:
            logger.error(f"Error running TaskAssignerAgent for project {self.project_id}: {e}", exc_info=True)
            return {
                "content": f"I'm sorry, I encountered an error while processing your request: {str(e)}"
            }

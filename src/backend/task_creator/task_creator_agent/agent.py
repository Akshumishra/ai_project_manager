import logging
from typing import Any, Dict, List
from uuid import UUID

from src.backend.utils.agent_utils import create_agent, get_last_ai_content, is_tool_successful
from src.backend.config import settings
from src.backend.task_creator.constants import TaskCreatorConstants as TaskConstants
from src.backend.task_creator.task_creator_agent.prompt import system_prompt as SYSTEM_PROMPT
from src.backend.task_creator.task_creator_agent.tools.save_tasks import make_save_tasks_tool

logger = logging.getLogger(__name__)


class TaskCreatorAgent:

    def __init__(self, user_id: UUID, project_id: UUID):
        self.user_id = user_id
        self.project_id = project_id
        self.agent = create_agent(
            model=TaskConstants.MODEL,
            temperature=TaskConstants.TEMPERATURE,
            tools=[
                make_save_tasks_tool(user_id, project_id)
            ],
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Executes the agent with the provided messages.
        Returns a dict with 'content' (final text) and 'tasks_saved' (bool).
        """
        logger.info(f"Running TaskCreatorAgent for project {self.project_id}")
        try:
            response = self.agent.invoke({"messages": messages})
        except Exception as e:
            logger.exception("TaskCreatorAgent.run() failed: %s", e)
            return {"content": str(e), "tasks_saved": False}

        response_messages = response.get("messages", [])
        
        tasks_saved = is_tool_successful(response_messages, "save_tasks")
        content = get_last_ai_content(response_messages)

        if not tasks_saved:
            logger.warning(
                "save_tasks tool was not called or returned an error. Response messages: %s",
                [getattr(m, "content", "")[:100] for m in response_messages]
            )

        return {
            "content": content,
            "tasks_saved": tasks_saved,
        }
import logging
from typing import Any, Dict, List
from uuid import UUID

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from src.backend.config import settings
from src.backend.task_creator.constants import TaskCreatorConstants as TaskConstants
from src.backend.task_creator.task_creator_agent.prompt import system_prompt
from src.backend.task_creator.task_creator_agent.tools.save_tasks import make_save_tasks_tool

logger = logging.getLogger(__name__)


class TaskCreatorAgent:

    def __init__(self, user_id: UUID, project_id: UUID):
        self.user_id = user_id
        self.project_id = project_id
        self.llm = self._create_llm()
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _create_llm(self):
        return ChatOpenAI(
            model=TaskConstants.MODEL,
            temperature=TaskConstants.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )

    def _create_tools(self):
        return [
            make_save_tasks_tool(
                self.user_id,
                self.project_id
            )
        ]

    def _create_agent(self):
        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=system_prompt,
        )

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Executes the agent with the provided messages.
        Returns a dict with 'content' (final text) and 'tasks_saved' (bool).
        """
        try:
            response = self.agent.invoke({"messages": messages})
        except Exception as e:
            logger.exception("TaskCreatorAgent.run() failed: %s", e)
            return {"content": str(e), "tasks_saved": False}

        response_messages = response.get("messages", [])

        # Detect if the save_tasks tool was called successfully
        tasks_saved = any(
            getattr(msg, "name", None) == "save_tasks"
            and "Successfully saved" in getattr(msg, "content", "")
            for msg in response_messages
        )

        last_message = response_messages[-1] if response_messages else None
        content = (
            getattr(last_message, "content", "")
            if last_message
            else str(response.get("output", ""))
        )

        if not tasks_saved:
            logger.warning(
                "save_tasks tool was not called or returned an error. Response messages: %s",
                [getattr(m, "content", "")[:100] for m in response_messages]
            )

        return {
            "content": content,
            "tasks_saved": tasks_saved,
        }
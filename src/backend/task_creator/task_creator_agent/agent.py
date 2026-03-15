from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from typing import Any, Dict, List
from uuid import UUID

from src.backend.config import Config
from src.backend.task_planner.constants import TaskCreatorConstants
from src.backend.task_planner.task_creator_agent.prompt import SYSTEM_PROMPT
from src.backend.task_planner.task_creator_agent.tools.save_tasks import make_save_tasks_tool


class TaskCreatorAgent:

    def __init__(self, user_id: UUID, project_id: UUID):
        self.user_id = user_id
        self.project_id = project_id
        self.llm = self._create_llm()
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _create_llm(self):
        return ChatOpenAI(
            model=TaskCreatorConstants.MODEL,
            temperature=TaskCreatorConstants.TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )

    def _create_tools(self):
        return [
            make_save_tasks_tool(
                self.user_id,
                self.project_id
            )
        ]

    def _create_agent(self):
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT
        )

    def _was_save_tool_called(self, response_messages: List[Any]) -> bool:
        for message in response_messages:
            tool_calls = getattr(message, "tool_calls", None) or []

            for tool_call in tool_calls:
                if tool_call.get("name") == "save_tasks":
                    return True

        return False

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:

        response = self.agent.invoke({
            "messages": messages
        })

        response_messages = response["messages"]
        last_message = response_messages[-1]

        content = getattr(last_message, "content", "")
        if not isinstance(content, str):
            content = str(content)

        return {
            "content": content,
            "tasks_saved": self._was_save_tool_called(response_messages),
        }
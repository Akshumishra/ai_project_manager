from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.backend.config import settings
from src.backend.task_creator.constants import TaskCreatorConstants as TaskConstants
from src.backend.task_creator.task_creator_agent.prompt import system_prompt
from src.backend.task_creator.task_creator_agent.tools.save_tasks import make_save_tasks_tool


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
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt
        )

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Executes the agent with the provided messages.
        """
        response = self.agent.invoke({
            "messages": messages
        })

        response_messages = response["messages"]
        last_message = response_messages[-1]
        
        content = getattr(last_message, "content", "")
        if not isinstance(content, str):
            content = str(content)
        
        # Check if the tool was called
        tasks_saved = any(
            getattr(msg, "name", None) == "save_tasks" for msg in response_messages
        )

        return {
            "content": content,
            "tasks_saved": tasks_saved,
        }
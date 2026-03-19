from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from uuid import UUID
from typing import Any, Dict, List

from src.backend.task_assigner.task_assigner_agent.prompt import SYSTEM_PROMPT
from src.backend.task_assigner.constants import TaskAssignerConstants
from src.backend.task_assigner.task_assigner_agent.tools.get_unassigned_tasks import make_get_unassigned_tasks_tool
from src.backend.task_assigner.task_assigner_agent.tools.get_project_members import make_get_project_members_tool
from src.backend.task_assigner.task_assigner_agent.tools.assign_task import make_assign_task_tool
from src.backend.config import settings


class TaskAssignerAgent:
    def __init__(self, user_id: UUID, project_id: UUID):
        self.user_id = user_id
        self.project_id = project_id
        self.llm = ChatOpenAI(
            model=TaskAssignerConstants.MODEL,
            temperature=TaskAssignerConstants.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
        self.tools = [
            make_get_unassigned_tasks_tool(project_id),
            make_get_project_members_tool(project_id),
            make_assign_task_tool()
        ]
        self.agent = self._create_agent()

    def _create_agent(self):
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT
        )

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        try:
            response = self.agent.invoke({
                "messages": messages
            })
            response_messages = response["messages"]
            last_message = response_messages[-1]

            content = getattr(last_message, "content", "")
            if not isinstance(content, str):
                content = str(content)

            return {
                "content": content
            }
        except Exception as e:
            print(f"Error running TaskAssignerAgent: {e}")
            return {
                "content": f"I'm sorry, I encountered an error while processing your request: {str(e)}"
            }

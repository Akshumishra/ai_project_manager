from typing import List

from langchain_openai import ChatOpenAI
from src.backend.config import settings
from src.backend.qa_chatbot.constants import QAAgentConstants
from langchain_core.messages import SystemMessage, BaseMessage
from langchain.agents import create_agent
from src.backend.qa_chatbot.qa_agent.prompt import SYSTEM_PROMPT
from src.backend.qa_chatbot.qa_agent.tools.run_sql_query import create_sql_query_tool
from src.backend.logger import get_logger

logger = get_logger("project_agent")

class ProjectAwareAgent:
    def __init__(
        self,
        project_id: str,
        slack_user_id: str,
        project_member_id: str,
    ):
        self.project_id        = project_id
        self.slack_user_id     = slack_user_id
        self.project_member_id = project_member_id

        logger.info(f"Initializing ProjectAwareAgent for project_id: {project_id}, user: {slack_user_id}")

        self.llm    = self._create_llm()
        self.tools  = self._create_tools()
        self.agent  = self._create_agent()

    def _create_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=QAAgentConstants.MODEL,
            temperature=QAAgentConstants.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
        )

    def _create_tools(self) -> list:
        return [
            create_sql_query_tool(
                project_id=self.project_id,
                slack_user_id=self.slack_user_id,
                project_member_id=self.project_member_id,
            )
        ]

    def _create_agent(self):
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
        )

    async def arun(self, messages: List[BaseMessage]) -> str:
        logger.info(f"Agent invoked with {len(messages)} messages")
        response = await self.agent.ainvoke({"messages": messages})
        final_response = response["messages"][-1].content
        logger.info("Agent execution completed successfully")
        return final_response



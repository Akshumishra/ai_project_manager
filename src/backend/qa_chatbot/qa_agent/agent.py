from typing import List

from langchain_openai import ChatOpenAI
from src.backend.config import Config
from src.backend.qa_chatbot.constants import AGENT_MODEL, AGENT_TEMPERATURE
from langchain_core.messages import SystemMessage, BaseMessage
from langchain.agents import create_agent
from src.backend.qa_chatbot.qa_agent.prompt import SYSTEM_PROMPT_TEMPLATE
from src.backend.qa_chatbot.qa_agent.tools.run_sql_query import make_run_sql_query_tool
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
            model=AGENT_MODEL,
            temperature=AGENT_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY,
        )

    def _create_tools(self) -> list:
        return [
            make_run_sql_query_tool(
                project_id=self.project_id,
                slack_user_id=self.slack_user_id,
                project_member_id=self.project_member_id,
            )
        ]

    def _create_agent(self):
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT_TEMPLATE,
        )

    def run(self, messages: List[BaseMessage]) -> str:
        logger.info(f"Agent invoked with {len(messages)} messages")
        response = self.agent.invoke({"messages": messages})
        final_response = response["messages"][-1].content
        logger.info("Agent execution completed successfully")
        return final_response



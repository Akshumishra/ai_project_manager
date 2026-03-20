from src.backend.utils.agent_utils import create_agent, get_last_ai_content, get_tool_call, extract_tool_args
from langchain_openai import ChatOpenAI
from typing import Any, Dict, List
from uuid import UUID

from src.backend.technical_doc.tech_doc_agent.prompt import SYSTEM_PROMPT
from src.backend.config import settings
from src.backend.technical_doc.constants import TechDocAgentConstants
from src.backend.technical_doc.tech_doc_agent.tools.save_tech_doc import make_save_tech_doc_tool
from src.backend.technical_doc.tech_doc_agent.tools.get_tech_doc_draft import make_get_tech_doc_draft_tool
import logging

logger = logging.getLogger(__name__)

class TechDocAgent:

    def __init__(self, user_id: UUID, project_id: UUID):
        self.user_id = user_id
        self.project_id = project_id
        self.agent = create_agent(
            model=TechDocAgentConstants.MODEL,
            temperature=TechDocAgentConstants.TEMPERATURE,
            tools=[
                make_save_tech_doc_tool(user_id, project_id),
                make_get_tech_doc_draft_tool(project_id)
            ],
            system_prompt=SYSTEM_PROMPT
        )

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        logger.info(f"Running TechDocAgent for project {self.project_id}")
        response = self.agent.invoke({
            "messages": messages
        })
        response_messages = response["messages"]
        
        content = get_last_ai_content(response_messages)
        
        doc_args = extract_tool_args(
            response_messages, 
            ["save_technical_specification"]
        )
        document = doc_args.get("document_markdown", "")

        return {
            "content": content,
            "document": document,
            "saved": bool(get_tool_call(response_messages, "save_technical_specification")),
        }


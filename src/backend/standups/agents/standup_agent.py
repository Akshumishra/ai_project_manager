import logging
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.backend.config import settings
from .prompt import (
    PARSE_REPLY_PROMPT,
    IDENTIFY_BLOCKER_PROMPT,
    SUMMARIZE_UPDATE_PROMPT,
    REFINE_STANDUP_PROMPT
)

logger = logging.getLogger(__name__)

class TaskUpdate(BaseModel):
    task_id: Optional[str] = Field(None, description="The ID of the task being updated from the provided list.")
    task_label: Optional[int] = Field(None, description="The numerical label of the task if mentioned (e.g. 4 for 'task 4').")
    task_title: str = Field(..., description="The title of the task.")
    new_status: str = Field(..., description="The updated status: 'todo', 'in_progress', 'completed', or 'blocked'.")
    comment: str = Field(..., description="A short summary of the progress reported.")
    deadline: Optional[str] = Field(None, description="The new deadline mentioned for this task (e.g., 'Friday', '2026-03-20').")
    complexity: Optional[str] = Field(None, description="The complexity of the task (e.g., 'Low', 'Medium', 'High').")

class DocUpdate(BaseModel):
    title: str = Field(..., description="The title of the document being updated (e.g., 'Project README', 'Architecture Notes').")
    content: str = Field(..., description="The new content or information to add/update in the document.")

class NewTask(BaseModel):
    title: str = Field(..., description="The title of the new task.")
    assignee: Optional[str] = Field(None, description="The name of the member assigned to the task (e.g., 'Akshita'), or None if for themselves.")
    description: Optional[str] = Field(None, description="A brief description of the task.")
    deadline: Optional[str] = Field(None, description="The deadline for the new task (e.g., 'Next Monday', 'Tomorrow').")
    complexity: Optional[str] = Field(None, description="The complexity of the new task (e.g., 'Low', 'Medium', 'High').")
    status: Optional[str] = Field("todo", description="The initial status of the task (e.g., 'todo', 'in_progress', 'completed', 'blocked').")

class Blocker(BaseModel):
    task_id: Optional[str] = Field(None, description="The ID of the task this blocker relates to, if applicable.")
    task_label: Optional[int] = Field(None, description="The numerical label of the task being blocked if mentioned (e.g. 4 for 'task 4').")
    blocked_by: Optional[str] = Field(None, description="Who or what is causing the delay.")
    reason: str = Field(..., description="The reason for the block or delay.")
    impact: str = Field(..., description="The impact of this blocker on work.")
    type: str = Field(..., description="Type: 'EXPLICIT' or 'INFERRED'.")
class ResolvedBlocker(BaseModel):
    task_id: Optional[str] = Field(None, description="The ID of the task being unblocked.")
    task_label: Optional[int] = Field(None, description="The numerical label of the task being unblocked if mentioned (e.g. 4 for 'task 4').")
    reason: str = Field(..., description="What was fixed or resolved.")

class StandupParsedResponse(BaseModel):
    updates: List[TaskUpdate] = Field(default_factory=list, description="List of task updates extracted.")
    doc_updates: List[DocUpdate] = Field(default_factory=list, description="List of documentation or project insight updates.")
    blockers: List[Blocker] = Field(default_factory=list, description="List of structured blockers or issues mentioned.")
    new_tasks: List[NewTask] = Field(default_factory=list, description="List of new tasks or activities mentioned, including assignments to others.")
    resolved_blockers: List[ResolvedBlocker] = Field(default_factory=list, description="List of previously reported blockers that the user explicitly mentions are now resolved (e.g., 'task 4 is fixed', 'No longer blocked by X').")
    sentiment: str = Field(..., description="Overall sentiment of the update (positive, neutral, at_risk).")

class IntelligentBlockerResult(BaseModel):
    blocker_detected: bool = Field(..., description="Whether a blocker was detected.")
    user_id: Optional[str] = Field(None, description="Identified user ID.")
    user_name: Optional[str] = Field(None, description="Identified user name.")
    task_id: Optional[str] = Field(None, description="Mapped task ID.")
    task_name: Optional[str] = Field(None, description="Mapped task name.")
    blocker_text: Optional[str] = Field(None, description="Cleaned blocker statement.")
    blocker_type: Optional[str] = Field(None, description="Type of blocker (e.g. dependency_blocker, technical_blocker, etc).")
    confidence_score: Optional[float] = Field(None, description="Confidence score 0-1.")
    reasoning: Optional[str] = Field(None, description="Short explanation of mapping.")

class StandupReplyAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key or settings.OPENAI_API_KEY,
            temperature=0
        )
        self.structured_llm = self.llm.with_structured_output(StandupParsedResponse)
        self.blocker_llm = self.llm.with_structured_output(IntelligentBlockerResult)

    def parse_reply(self, user_name: str, reply_text: str, active_tasks: List[dict], active_blockers: List[dict] = None, team_members: List[str] = None, message_date: Optional[datetime] = None, has_in_progress_tasks: bool = True) -> StandupParsedResponse:
        """
        Parses a natural language standup reply into structured data using LangChain.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", PARSE_REPLY_PROMPT),
            ("user", "Developer Reply: {reply_text}")
        ])

        ref_date = message_date or datetime.now()
        today_str = ref_date.strftime("%Y-%m-%d, %A")
        
        in_progress_state = (
            "The developer currently HAS IN-PROGRESS TASKS. Track updates against them."
            if has_in_progress_tasks else
            "⚠️ CRITICAL: This developer currently has NO tasks 'in_progress'. You MUST carefully analyze their reply to identify which of the provided 'todo' tasks they are starting or picking up, and set its `new_status` to 'in_progress'."
        )

        try:
            chain = prompt | self.structured_llm
            result = chain.invoke({
                "user_name": user_name,
                "has_in_progress_state": in_progress_state,
                "reply_text": reply_text,
                "active_tasks_json": json.dumps(active_tasks, indent=2),
                "active_blockers_json": json.dumps(active_blockers or [], indent=2),
                "team_members_json": json.dumps(team_members or [], indent=2),
                "today": today_str
            })
            logger.info(f"LangChain parsed standup reply for {user_name}")
            return result
        except Exception as e:
            logger.error(f"Error parsing standup reply with LangChain: {e}")
            # Fallback
            return StandupParsedResponse(
                updates=[],
                blockers=[],
                new_tasks=[],
                sentiment="unknown"
            )

    def identify_blocker(self, standup_message: str, members_with_active_tasks: str, standup_summaries: str, todo_tasks: str) -> IntelligentBlockerResult:
        """
        Uses an intelligent prompt to analyze a standup message for explicit and inferred blockers.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", IDENTIFY_BLOCKER_PROMPT),
            ("user", "New Standup Message:\n{standup_message}\n\nNow process the input and return the structured output.")
        ])

        try:
            chain = prompt | self.blocker_llm
            result = chain.invoke({
                "members_with_active_tasks": members_with_active_tasks,
                "standup_summaries": standup_summaries,
                "todo_tasks": todo_tasks,
                "standup_message": standup_message
            })
            logger.info("Successfully identified blocker using intelligent prompt.")
            return result
        except Exception as e:
            logger.error(f"Error identifying blocker: {e}")
            return IntelligentBlockerResult(blocker_detected=False)

    def summarize_update(self, user_name: str, reply_text: str, action_logs: List[str]) -> str:
        """
        Generates a professional, one-sentence insight summary of a developer's update.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", SUMMARIZE_UPDATE_PROMPT),
            ("user", "Summarize this update.")
        ])

        try:
            actions_list = "\n".join([f"- {a}" for a in action_logs])
            chain = prompt | self.llm
            result = chain.invoke({
                "user_name": user_name,
                "reply_text": reply_text,
                "actions_list": actions_list
            })
            summary = result.content.strip() if hasattr(result, 'content') else str(result).strip()
            # Ensure it ends with a period
            if summary and not summary.endswith("."):
                summary += "."
            return summary
        except Exception as e:
            logger.error(f"Error summarizing standup update: {e}")
            # Fallback to first sentence
            return reply_text.split(".", 1)[0] + "."

    def refine_standup_prompt(self, project_name: str, raw_prompt: str) -> str:
        """
        Refines the final standup prompt to remove redundancies and ensure peak professionalism.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", REFINE_STANDUP_PROMPT),
            ("user", "{raw_prompt}")
        ])

        try:
            chain = prompt | self.llm
            result = chain.invoke({
                "project_name": project_name,
                "raw_prompt": raw_prompt
            })
            refined = result.content.strip() if hasattr(result, 'content') else str(result).strip()
            return refined
        except Exception as e:
            logger.error(f"Error refining standup prompt: {e}")
            return raw_prompt

import logging
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.backend.config import settings

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
            ("system", """
You are an expert Project Manager AI. Your job is to parse a developer's standup reply and extract structured updates.
The developer is {user_name}.

{has_in_progress_state}

Below is a list of their RELEVANT TASKS (either assigned to them or available unassigned TODOs):
{active_tasks_json}

Below is a list of their CURRENT ACTIVE BLOCKERS:
{active_blockers_json}

Below is a list of ALL PROJECT TEAM MEMBERS:
{team_members_json}

Please analyze the developer's reply and extract the updates, blockers, and sentiment.

Rules:
- **Task Identification & In-Progress Status**: 
  - Carefully identify which task(s) from the provided list the developer is currently working on, starting, or continuing.
  - If the developer mentions "working on", "starting", "continuing", "taking", "picking up", or describes progress on a task from the list, you MUST set its `new_status` to **'in_progress'**.
  - **CRITICAL**: If the user explicitly states a task is completed, done, or finished, set its `new_status` to **'completed'**. You MUST NOT extract it as a blocker under any circumstances.
  - **CRITICAL**: If the person has no tasks currently 'in_progress' in the system, pay extra attention to identify which 'todo' task they are starting based on their reply and set it to 'in_progress'.
- If they mention ANY task or activity NOT in the provided list, you MUST put it in 'new_tasks'. 
- This includes activities they are currently doing (e.g., 'I am starting X') or assigning to others.
- For 'new_tasks', generate a **professional, concise description** for the 'description' field (e.g., "Implement login API" instead of "I am working on login").
- For 'new_tasks', identify the 'assignee' by name. **CRITICAL**: Use the provided list of TEAM MEMBERS to resolve mentions to names. If they mention a name that "mostly" matches a team member (e.g., "Akshita" for "Akshita Mishra"), use the full name from the list. If they mention "self" or don't specify, leave it null.
- Extract any mentioned **deadlines** for new tasks or updates. **IMPORTANT**: Convert relative deadlines (e.g., "by Friday", "tomorrow", "next week") into an exact date in **YYYY-MM-DD** format based on today's date ({today}). If the year is ambiguous, assume 2026.
- Extract ANY mentioned **complexity** (e.g., "Low", "Medium", "High") for tasks. **MANDATORY**: If the user does NOT mention complexity, you MUST infer it yourself based on the task effort and put it in the 'complexity' field.
- **Blocker Intelligence**: Closely analyze the reply for any blockers or dependencies. You MUST extract ALL blockers mentioned.
  - **Task Identification**: If the user mentions a task by its label (e.g., "task 4" or "blocked in 4"), you MUST set `task_label` to that number.
  - **CRITICAL**: The `new_status` or `status` of any task MUST be one of: **'todo', 'in_progress', 'completed', 'blocked'**.
  - **CRITICAL**: If the user reports being "stuck", "waiting", or "blocked" for a specific task (even if they also say they are "starting" it), the `new_status` or `status` of that task MUST be **'blocked'**.
  - **EXPLICIT**: If the user directly says they are blocked or stuck.
  - **INFERRED**: If the user mentions waiting for someone, or phrases like "I would have finished but...", or "still haven't heard back from X".
  - For EACH blocker, identify:
    - `blocked_by`: The person (e.g., 'Akshita') or thing (e.g., 'API keys') causing the delay.
    - `reason`: A concise explanation of why work is delayed.
    - `impact`: Assessment of risk ('high', 'medium', 'low').
    - `type`: 'EXPLICIT' or 'INFERRED'.
- **Blocker Resolutions**: Identify if the developer mentions that any previously reported issues, blockers, or dependencies are now **resolved, fixed, or no longer an issue**. Put these into `resolved_blockers`. 
  - If they mention a task label (e.g. "task 4 is resolved"), you MUST set `task_label` to 4.
- If they mention updating documentation, requirements, or project notes, extract it into 'doc_updates'.
- For 'doc_updates', provide a clear 'content' field that can be used as a new document block.
- Be concise.
"""),
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
            ("system", """
You are an intelligent Standup Agent responsible for identifying and structuring blockers in a project.

Your goal is to:
1. Identify WHICH project member a blocker belongs to.
2. Identify WHICH TASK the blocker is associated with.
3. Handle both:
   - Explicit blockers (clearly stated)
   - Inferred blockers (implicit issues, delays, confusion, dependencies)

You MUST follow a 2-step approach:
------------------------------------

STEP 1: THINK AND CREATE A PLAN (DO NOT OUTPUT THIS PLAN DIRECTLY)
- Analyze all provided data sources carefully:
  
  A. Project Members with their current in-progress tasks
  B. Past 10 days standup summaries
  C. Past 14 days TODO tasks of all members

- Based on patterns, context, and history:
  - Map how people usually refer to their tasks
  - Understand writing styles of different members
  - Identify recurring blockers or dependencies
  - Detect ownership patterns (who usually works on what)

- Build an internal reasoning plan:
  - How to match blocker -> person
  - How to match blocker -> task (even if task name is not explicitly mentioned)
  - How to infer blockers from vague or indirect language

------------------------------------

STEP 2: EXECUTE THE PLAN

Given a new standup message, you must:

1. Detect if a blocker exists:
   - Explicit (e.g., "I am blocked", "waiting for", "issue with")
   - Implicit (e.g., "still working", "not able to proceed", "stuck", "dependency pending")

2. Identify the USER:
   - Use message sender if available
   - Otherwise infer from context/history

3. Identify the TASK:
   - Match keywords with task names
   - Use historical summaries and TODOs for fuzzy matching
   - If multiple matches, choose the most relevant based on context

4. Classify blocker:
   - dependency_blocker
   - technical_blocker
   - unclear_requirements
   - external_blocker
   - other

5. Generate a CLEAN structured output matching the JSON schema.

------------------------------------

IMPORTANT RULES:
- CRITICAL: If a user mentions that a task is COMPLETED, DONE, FINISHED, or RESOLVED (e.g. 'the security is now done from my side', 'finished task 5'), this is NOT a blocker! You MUST return blocker_detected = false.
- NEVER hallucinate users or tasks not present in the input
- If uncertain, choose best possible match with lower confidence score
- If no blocker is found, return blocker_detected = false
- Keep reasoning concise (1-2 lines max)
- Focus on accuracy over verbosity

------------------------------------

INPUT DATA:

Project Members with Active Tasks:
{members_with_active_tasks}

Past 10 Days Standup Summaries:
{standup_summaries}

Past 14 Days TODO Tasks:
{todo_tasks}
"""),
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
            ("system", """
You are a Project Manager AI. Summarize the following standup update into a SINGLE professional sentence (max 20 words).
The developer is {user_name}.

Raw Reply: "{reply_text}"
Structured Actions Taken:
{actions_list}

Rules:
- Focus on accomplishments (completions), significant progress, or important new assignments.
- Use professional active voice (e.g., "Completed X", "Assigned Y to Z", "Started Z").
- **REDUNDANCY ALERT**: If there are BLOCKERS listed in the actions, do NOT repeat the details of those blockers in this summary (e.g., don't say "Aarushi is blocked by X"). The blockers will be displayed in a separate dedicated section. Focus on what was achieved DESPITE or alongside those blockers.
- **EMPTY UPDATE RULE**: If the only actions taken are blockers (e.g., the only action log mentions a BLOCKER), do NOT hallucinate a completion. Instead, return: "No progress updates reported."
- Do NOT include routine "todo" or "inprogress" status updates unless they are the only thing mentioned.
- If multiple things happened, pick the most significant one.
- Return ONLY the summary sentence. No preamble.
"""),
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
            ("system", """
You are a Senior Project Manager known for clear, high-impact communication.
Your task is to refine the following morning standup message for the project "{project_name}".

STRICT DATA INTEGRITY RULES:
1. **DO NOT ADD NEW DATA**: You must only work with the text provided in the user message. Do NOT add any sections, bullets, or information that is not already present in the "raw_prompt".
2. **DO NOT HALLUCINATE FROM EXAMPLES**: The examples provided in these instructions are for illustrative purposes only. Do NOT include them in the final output unless they are actually in the "raw_prompt".
3. **DO NOT ADD MISSING SECTIONS**: If a section (like "Key Insights" or "Member Blockers") is not in the "raw_prompt", you MUST NOT add it.

SURGICAL REDUNDANCY REMOVAL:
- Compare every bullet in "💡 Key Insights from Last Standup" (if it exists) with the entries in "🚧 Member Blockers from Last Standup" (if it exists).
- If a member has a blocker listed, review their "Key Insight".
- If the insight is ONLY about the blocker [Example: "Member is waiting for a key"], DELETE that insight bullet.
- If the insight contains progress AND a blocker mention [Example: "Member completed UI but is waiting for a key"], STRIP only the blocker mention [Result: "Member completed UI"].
- The "Key Insights" section (if present) should ONLY contain positive progress, accomplishments, or significant non-blocking updates.

STYLE & FORMATTING:
- Ensure the message feels premium, professional, and high-energy.
- Keep the structure (Headers, Emojis) mostly intact.
- **DATA PROTECTION**: Do NOT remove or alter the following sections (they are data-driven):
    1. "🚧 *Current Member Blockers:*"
    2. "🚧 *Tasks on Hold:*"
    3. "🚨 *CRITICAL: Deadline Risks Identified*"
    4. "💡 *Insights from Last Standup:*"
    5. "🆕 *Tasks Added Last Standup:*"
    6. Any section containing task lists by member.
- **EMOJI RULE**: Do NOT add any emojis to individual bulleted sentences or task names. Emojis should ONLY exist in the main section headings.
- You may only refine the text within existing sections to remove repetitions or improve phrasing.
- Return ONLY the refined Slack message text.
"""),
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
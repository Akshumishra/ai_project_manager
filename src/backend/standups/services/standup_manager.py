import logging
import uuid
import re
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.task import Task, TaskStatus
from src.backend.model.task_log import TaskLog
from src.backend.model.project import ProjectMember, Project, ProjectSlackDetail
from src.backend.model.user import User
from src.backend.model.document import Document, DocumentBlock
from src.backend.model.blocker import Blocker
from src.backend.slack.services.slack_service import SlackService
from src.backend.standups.services.standup_generator import StandupGenerator
from src.backend.standups.agents.standup_agent import StandupReplyAgent, StandupParsedResponse, NewTask

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

logger = logging.getLogger(__name__)

class StandupManager:
    def initiate_all_standups(self) -> Dict[str, str]:
        """
        Initiates standups for all projects that have a Slack channel configured.
        Returns a mapping of project_id to message_ts.
        """
        results = {}
        # Fetch all project slack details
        details = self.db.query(ProjectSlackDetail).all()
        
        for detail in details:
            if not detail.channel_id:
                continue
                
            project_id_str = str(detail.project_id)
            logger.info(f"Auto-triggering standup for project {project_id_str} in channel {detail.channel_id}")
            
            ts = self.initiate_standup(project_id_str, detail.channel_id)
            if ts:
                results[project_id_str] = ts
                
        return results

    def __init__(self, db: Session):
        self.db = db
        self.slack_service = SlackService()
        self.generator = StandupGenerator(db)
        self.agent = StandupReplyAgent()

    def initiate_standup(self, project_id: str, channel_id: str) -> Optional[str]:
        """
        Starts a new standup session by posting a prompt to Slack.
        """
        try:
            # 1. Fetch active tasks, deadline risks, and persistent blockers
            grouped_tasks, overdue_tasks, suggestions = self.generator.fetch_active_tasks(project_id)
            active_blockers = self.generator.fetch_active_blockers(project_id)
            
            # 2. Get project name
            from src.backend.model.project import Project
            project = self.db.query(Project).get(project_id)
            project_name = project.name if project else "Project"

            # 3. Fetch historical highlights and last summary insights
            historical_highlights, summary_insights = self._get_historical_highlights(project_id)

            # 4. Identify members who missed the last standup
            missed_update_members = self._get_missed_update_members(project_id, grouped_tasks)
            
            # 5. Generate the standup prompt
            raw_prompt = self.generator.generate_standup_prompt(
                project_name, 
                grouped_tasks, 
                overdue_tasks,
                suggestions,
                historical_highlights,
                active_blockers,
                missed_update_members,
                summary_insights
            )
            
            # 5. Refine prompt to remove redundancies
            prompt_text = self.agent.refine_standup_prompt(project_name, raw_prompt)

            # 6. Post to Slack
            ts = self.slack_service.post_message(channel_id, prompt_text)
            
            # 6. Record in DB
            standup = Standup(
                project_id=uuid.UUID(str(project_id)),
                slack_channel_id=channel_id,
                message_ts=ts,
                prompt=prompt_text  # Store the initial prompt separately
            )
            self.db.add(standup)
            self.db.commit()
            
            logger.info(f"Initiated standup for project {project_id} at {ts}")
            return ts
        except Exception as e:
            logger.error(f"Failed to initiate standup: {e}", exc_info=True)
            self.db.rollback()
            return None

    def _get_historical_highlights(self, project_id: str) -> tuple[Dict[str, Dict[str, Any]], List[str]]:
        """
        Retrieves highlights (summaries, blockers) from the last completed standup session.
        Uses AI to summarize the updates professionally.
        """
        standups = (
            self.db.query(Standup)
            .filter(Standup.project_id == uuid.UUID(str(project_id)))
            .order_by(Standup.created_at.desc())
            .all()
        )

        fallback: Dict[str, Dict[str, Any]] = {}
        selected_highlights: Optional[Dict[str, Dict[str, Any]]] = None

        for standup in standups:
            if not standup.updates:
                continue

            highlights = self._build_standup_highlights(standup)
            if not highlights:
                continue

            if not fallback:
                fallback = highlights

            if self._highlights_have_blockers(highlights):
                selected_highlights = highlights
                break

        if not selected_highlights:
            selected_highlights = fallback

        latest_summary_standup = (
            self.db.query(Standup)
            .filter(Standup.project_id == uuid.UUID(str(project_id)))
            .filter(Standup.summary.isnot(None))
            .order_by(Standup.created_at.desc())
            .first()
        )
        summary_insights = self._extract_summary_insights(
            latest_summary_standup.summary if latest_summary_standup else None
        )

        return selected_highlights, summary_insights

    def _project_has_active_blocked_tasks(self, project_id: str) -> bool:
        grouped_tasks, _, _ = self.generator.fetch_active_tasks(project_id)
        return any(task.get("status") == "blocked" for tasks in grouped_tasks.values() for task in tasks)

    def _get_missed_update_members(self, project_id: str, grouped_tasks: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """
        Identifies members who missed the last standup session but have active tasks.
        """
        # Get the most recent standup for this project
        last_standup = (
            self.db.query(Standup)
            .filter(Standup.project_id == uuid.UUID(str(project_id)))
            .order_by(Standup.created_at.desc())
            .offset(0) # The one we are about to create doesn't exist yet, so the latest is the real previous one
            .first()
        )
        
        if not last_standup:
            return []
            
        # Get all users who provided an update for the last standup
        update_user_ids = {u.user_id for u in last_standup.updates}
        
        missed_members = []
        # Check all members who have active tasks
        for member_name, tasks in grouped_tasks.items():
            # Find the user id for this member_name
            # This is slightly inefficient but grouped_tasks is small
            member = self.db.query(ProjectMember).join(User).filter(
                ProjectMember.project_id == uuid.UUID(str(project_id)),
                User.name == member_name
            ).first()
            
            if member and member.user_id not in update_user_ids:
                missed_members.append(member_name)
                
        return missed_members

    def _build_standup_highlights(self, standup: Standup) -> Dict[str, Dict[str, Any]]:
        highlights: Dict[str, Dict[str, Any]] = {}

        for update in standup.updates:
            user_name = update.user.name if update.user else "Unknown"
            
            # Initialize for this member if not seen yet in THIS standup session
            if user_name not in highlights:
                highlights[user_name] = {
                    "raw_texts": [],
                    "action_lists": [],
                    "blockers": [],
                    "new_tasks": []
                }

            # Collect blockers and new tasks
            for log in update.action_logs:
                if "BLOCKER" in log.action_taken:
                    parsed_blk = self._parse_blocker_action(log.action_taken)
                    highlights[user_name]["blockers"].append(parsed_blk)

                new_task_name = self._extract_new_task_name(log.action_taken, user_name)
                if new_task_name:
                    highlights[user_name]["new_tasks"].append(new_task_name)

            # Collect text and actions for summarization
            highlights[user_name]["raw_texts"].append(update.reply_text)
            highlights[user_name]["action_lists"].extend([log.action_taken for log in update.action_logs])

        # Final pass to generate a unified professional summary per member
        for user_name, data in highlights.items():
            combined_text = "\n".join(data["raw_texts"])
            summary = self.agent.summarize_update(user_name, combined_text, data["action_lists"])
            
            highlights[user_name] = {
                "summary": summary,
                "blockers": data["blockers"],
                "new_tasks": data["new_tasks"]
            }

        if not self._project_has_active_blocked_tasks(str(standup.project_id)):
            for data in highlights.values():
                data["blockers"] = []
        return highlights

    def _highlights_have_blockers(self, highlights: Dict[str, Dict[str, Any]]) -> bool:
        return any(hl.get("blockers") for hl in highlights.values())

    def _extract_summary_insights(self, summary_text: Optional[str]) -> List[str]:
        if not summary_text:
            return []
        lines = [line.strip() for line in summary_text.splitlines()]
        insights = []
        for line in lines:
            if not line:
                continue
            if line.startswith("•"):
                insight = line.lstrip("•").strip()
                # Keep the next standup prompt clean: "to self" is an internal assignment artifact,
                # not useful context for the team-facing message.
                insight = re.sub(r"\s+to\s+self\b", "", insight, flags=re.IGNORECASE)
                insight = re.sub(r"\s{2,}", " ", insight).strip()
                if insight and insight != "Great job team! Keep the momentum going. :chart_with_upwards_trend:":
                    insights.append(insight)
        return insights

    def _parse_blocker_action(self, action_text: str) -> Dict[str, str]:
        """
        Parses a BLOCKER action log entry into structured details.
        Falls back to capturing the whole message when the regex misses.
        """
        match = re.search(
            r"BLOCKER \((.*?)\): Blocked (?:by (.*?) )?due to: (.*?)\.? Impact: (.*?)\.",
            action_text,
        )
        if match:
            return {
                "type": match.group(1),
                "blocked_by": match.group(2) or "N/A",
                "reason": match.group(3).strip(),
                "impact": match.group(4).strip(),
            }

        reason = action_text.split(": ", 1)[1] if ": " in action_text else action_text
        return {
            "type": "UNKNOWN",
            "blocked_by": "N/A",
            "reason": reason.strip(),
            "impact": "unknown",
        }

    def _extract_new_task_name(self, action_text: str, user_name: str) -> Optional[str]:
        prefixes = ("TODO: ", "IN_PROGRESS: ", "COMPLETED: ", "BLOCKED: ")
        for prefix in prefixes:
            if action_text.startswith(prefix):
                task_part = action_text.split(": ", 1)[1]
                if f" to {user_name}" in task_part:
                    task_part = task_part.split(f" to {user_name}", 1)[0]
                if " to self" in task_part:
                    task_part = task_part.split(" to self", 1)[0]
                return task_part.strip()
        return None

    def process_new_replies(self, standup_id: str):
        """
        Fetches new replies from the Slack thread and processes them.
        """
        # Convert string to UUID if needed
        try:
            standup_uuid = uuid.UUID(standup_id) if isinstance(standup_id, str) else standup_id
        except ValueError:
            logger.error(f"Invalid standup_id format: {standup_id}")
            return
        
        standup = self.db.query(Standup).filter(Standup.id == standup_uuid).first()
        if not standup:
            logger.warning(f"Standup {standup_id} not found for processing replies")
            return

        # Fetch replies from Slack
        replies = self.slack_service.list_replies(standup.slack_channel_id, standup.message_ts)
        
        # Skip the first message (the prompt itself)
        for reply in replies[1:]:
            user_slack_id = reply.get("user")
            raw_text = reply.get("text", "")
            reply_ts = reply.get("ts")
            logger.error(f"DEBUG: Processing reply from {user_slack_id} with text '{raw_text[:20]}...'")

            # Resolve Slack mentions to names before cleaning/AI parsing
            # Find all <@U...> mentions
            mentions = re.findall(r'<@(U[A-Z0-9]+)>', raw_text)
            text = raw_text
            for mention_id in mentions:
                mention_member = self.db.query(ProjectMember).filter(
                    ProjectMember.project_id == standup.project_id,
                    ProjectMember.slack_id == mention_id
                ).first()
                if mention_member:
                    mention_user = self.db.query(User).get(mention_member.user_id)
                    if mention_user:
                        text = text.replace(f"<@{mention_id}>", mention_user.name)
            
            # Now clean remaining formatting
            text = re.sub(r'[*_]{1,2}', '', text)
            text = text.strip()

            # Check if already processed by slack_ts (robust) or cleaned text (fallback)
            existing = self.db.query(StandupUpdate).filter(
                StandupUpdate.standup_id == standup.id,
                StandupUpdate.deleted_at.is_(None)
            ).filter(
                (StandupUpdate.slack_ts == reply_ts) | (StandupUpdate.reply_text == text)
            ).first()
            
            if existing:
                continue

            try:
                # 1. Identify project member
                member = self.db.query(ProjectMember).filter(
                    ProjectMember.project_id == standup.project_id,
                    ProjectMember.slack_id == user_slack_id
                ).first()
                
                if not member:
                    if user_slack_id == "U0AJZR4M0DD": # Skip bot itself silently
                        continue
                    logger.warning(f"Reply from unknown Slack user {user_slack_id} in standup {standup_id}")
                    continue

                # 2. Extract structured data via AI
                active_tasks, _, suggestions = self.generator.fetch_active_tasks(str(standup.project_id))
                user = self.db.query(User).get(member.user_id)
                user_name = user.name if user else "Developer"
                
                # Focus context: only give AI tasks for this user + unassigned suggestions
                user_tasks = active_tasks.get(user_name, [])
                user_suggestions = suggestions.get(user_name, [])
                unassigned_suggestions = []
                for s_list in suggestions.values():
                    unassigned_suggestions.extend([s for s in s_list if s.get("is_unassigned")])
                
                # Deduplicate unassigned suggestions (they might already be in user_suggestions)
                seen_ids = {t["id"] for t in user_suggestions}
                unique_unassigned = [s for s in unassigned_suggestions if s["id"] not in seen_ids]

                # Determine if user already has in-progress tasks
                has_in_progress_tasks = any(t.get("status") == "in_progress" for t in user_tasks)
                
                # Combine for the agent context
                flat_tasks = user_tasks + user_suggestions + unique_unassigned
                members_with_active_tasks = json.dumps(active_tasks, indent=2)

                # Fetch Past 10 Days Standup Summaries
                cutoff_10d = datetime.now(timezone.utc) - timedelta(days=10)
                past_standups = self.db.query(Standup).filter(
                    Standup.project_id == standup.project_id,
                    Standup.created_at >= cutoff_10d,
                    Standup.summary.isnot(None)
                ).order_by(Standup.created_at.desc()).limit(10).all()
                standup_summaries = "\n".join([f"Date: {s.created_at}, Summary: {s.summary}" for s in past_standups])

                # Fetch Past 14 Days TODO Tasks
                cutoff_14d = datetime.now(timezone.utc) - timedelta(days=14)
                past_todos = self.db.query(Task).filter(
                    Task.project_id == standup.project_id,
                    Task.status == TaskStatus.TODO,
                    Task.created_at >= cutoff_14d,
                    Task.deleted_at.is_(None)
                ).all()
                todo_tasks_str = "\n".join([f"ID: {t.id}, Title: {t.title}" for t in past_todos])
                
                # Call Intelligent Blocker identification
                try:
                    intelligent_blocker = self.agent.identify_blocker(
                        standup_message=text,
                        members_with_active_tasks=members_with_active_tasks,
                        standup_summaries=standup_summaries,
                        todo_tasks=todo_tasks_str
                    )
                except Exception as e:
                    logger.error(f"Failed to identify blocker: {e}")
                    from src.backend.standups.agents.standup_agent import IntelligentBlockerResult
                    intelligent_blocker = IntelligentBlockerResult(blocker_detected=False)

                # --- Task Selection Pre-Processing ---
                # Detect "I am taking task X" patterns and update the DB BEFORE AI parsing.
                # The task is flushed so the AI sees it as in_progress in subsequent queries.
                # The StandupUpdate doesn't exist yet here, so we just flush the task change;
                # the StandupActionLog will be written after the update is saved below.
                selected_task = self._detect_task_selection(text, member, standup)

                # Calculate message date from Slack TS for relative deadline logic
                msg_date = None
                if reply_ts:
                    msg_date = datetime.fromtimestamp(float(reply_ts), tz=timezone.utc)

                # Get list of all project member names for context
                all_members = self.db.query(User).join(ProjectMember).filter(
                    ProjectMember.project_id == standup.project_id
                ).all()
                member_names = [u.name for u in all_members]

                # Get currently active blockers for this user for AI context
                active_blockers_db = self.db.query(Blocker).filter(
                    Blocker.project_id == standup.project_id,
                    Blocker.user_id == member.user_id,
                    Blocker.resolved_at.is_(None)
                ).all()
                flat_blockers = [{"reason": b.reason, "task_title": b.task.title if b.task else None} for b in active_blockers_db]

                parsed = self.agent.parse_reply(user_name, text, flat_tasks, active_blockers=flat_blockers, team_members=member_names, message_date=msg_date, has_in_progress_tasks=has_in_progress_tasks)

                # Inject Intelligent Blocker if found
                if intelligent_blocker.blocker_detected:
                    from src.backend.standups.agents.standup_agent import Blocker as AgentBlocker
                    new_agent_blocker = AgentBlocker(
                        task_id=intelligent_blocker.task_id if intelligent_blocker.task_id and intelligent_blocker.task_id != "null" else None,
                        task_label=None,
                        blocked_by="Unknown",
                        reason=intelligent_blocker.blocker_text or "Inferred blocker",
                        impact=intelligent_blocker.blocker_type or "medium",
                        type="INFERRED" if intelligent_blocker.blocker_type != "explicit" else "EXPLICIT"
                    )
                    # Deduplicate: if not already found in parsed.blockers
                    is_dup = False
                    ignore_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by", "with", "from", "blocked", "resolved", "fixed", "no", "longer", "issue", "i"}
                    n_words = set(re.findall(r'\w+', new_agent_blocker.reason.lower())) - ignore_words
                    for pb in parsed.blockers:
                        # Exact same task ID? It's the same blocker.
                        if new_agent_blocker.task_id and pb.task_id and str(new_agent_blocker.task_id) == str(pb.task_id):
                            is_dup = True
                            break
                        # Keyword overlap for non-task blockers
                        pb_words = set(re.findall(r'\w+', pb.reason.lower())) - ignore_words
                        if n_words and pb_words and len(n_words.intersection(pb_words)) >= (min(len(n_words), len(pb_words)) * 0.4):
                            is_dup = True
                            break
                            
                    if not is_dup:
                        parsed.blockers.append(new_agent_blocker)

                # 3. Save raw update (already cleaned)
                update = StandupUpdate(
                    standup_id=standup.id,
                    user_id=member.user_id,
                    reply_text=text,
                    slack_ts=reply_ts
                )
                self.db.add(update)
                self.db.flush()

                # 4. Write StandupActionLog for task selection (now that update.id exists)
                if selected_task:
                    self._log_task_selection_action(update.id, selected_task)

                # 5. Apply AI-parsed updates
                self._apply_parsed_updates(update.id, parsed)
                self.db.commit() # Commit each reply individually to be safe

            except Exception as e:
                logger.error(f"Error processing reply from {user_slack_id}: {e}")
                self.db.rollback()
                continue

    def _safe_status_conversion(self, status_str: str, default: TaskStatus = TaskStatus.TODO) -> TaskStatus:
        """Safely converts a string to TaskStatus enum."""
        if not status_str:
            return default
        try:
            return TaskStatus(status_str.lower())
        except ValueError:
            logger.warning(f"Unknown task status: '{status_str}'. Defaulting to {default.value}")
            return default

    def _apply_parsed_updates(self, update_id: uuid.UUID, parsed: StandupParsedResponse):
        """
        Applies the changes extracted by the AI Agent to the database.
        """
        standup_update = self.db.query(StandupUpdate).get(update_id)
        standup = self.db.query(Standup).get(standup_update.standup_id)
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == standup.project_id,
            ProjectMember.user_id == standup_update.user_id
        ).first()

        for up in parsed.updates:
            try:
                task = None
                if not up.task_id or up.task_id == "null":
                    # Fallback: Try to find an existing task by name for this member/project
                    
                    # Try finding by label first if provided
                    if hasattr(up, 'task_label') and up.task_label:
                        existing_task = self.db.query(Task).filter(
                            Task.project_id == standup.project_id,
                            Task.label == up.task_label,
                            Task.deleted_at.is_(None)
                        ).first()
                        if existing_task:
                            logger.info(f"Resolved task via label {up.task_label} (ID: {existing_task.id})")
                            task = existing_task
                        else:
                            task = None
                    else:
                        existing_task = self._find_existing_task(standup.project_id, up.task_title, member.id if member else None)
                        if existing_task:
                            logger.info(f"Deduplication: Found existing task '{up.task_title}' (ID: {existing_task.id}) for update.")
                            task = existing_task 
                        else:
                            task = None

                    if not task:
                        # If truly no existing task found, treat it as a new task
                        new_t = NewTask(
                            title=up.task_title,
                            assignee=None, # Assigned to self
                            description=up.comment,
                            deadline=up.deadline,
                            complexity=up.complexity,
                            status=up.new_status
                        )
                        parsed.new_tasks.append(new_t)
                        continue
                else:
                    task = self.db.query(Task).get(up.task_id)
                if not task:
                    continue

                # Auto-assign if task is unassigned and user is taking it
                if member and task.project_member_id is None:
                    logger.info(f"Auto-assigning task {task.label} to {member.user.name if member.user else 'current user'}")
                    task.project_member_id = member.id

                # Record change
                old_status = task.status.value.lower()
                new_status_obj = self._safe_status_conversion(up.new_status)
                new_status_lower = new_status_obj.value
                
                if new_status_lower != old_status:
                    task.status = new_status_obj
                    
                # Update deadline if provided
                if up.deadline:
                    logger.info(f"Parsing deadline for task update: '{up.deadline}'")
                    parsed_dt = self._parse_deadline(up.deadline)
                    if parsed_dt:
                        logger.info(f"Setting task.deadline to: {parsed_dt}")
                        task.deadline = parsed_dt
                    else:
                        logger.warning(f"Could not parse deadline string: '{up.deadline}'")
                
                # Update complexity if provided
                if up.complexity:
                    task.complexity = up.complexity

                # Record change in TaskLog
                log_entry = f"Status: {new_status_lower}. Comment: {up.comment}"
                if up.deadline:
                    log_entry += f" Deadline: {up.deadline}"
                if up.complexity:
                    log_entry += f" Complexity: {up.complexity}"
                log_entry += " (via StandUp Agent)"
                
                task_log = TaskLog(task_id=task.id, log=log_entry)
                self.db.add(task_log)
                
                # Automated Blocker Resolution: 
                # If a task is moved to in_progress or completed, mark any persistent blockers for it as resolved.
                if new_status_lower in [TaskStatus.IN_PROGRESS.value, TaskStatus.COMPLETED.value]:
                    active_blockers = self.db.query(Blocker).filter(
                        Blocker.task_id == task.id,
                        Blocker.resolved_at.is_(None)
                    ).all()
                    for b in active_blockers:
                        b.resolved_at = datetime.now(timezone.utc)
                        logger.info(f"Auto-resolved blocker {b.id} because task {task.title} moved to {new_status_lower}.")
                        
                        # Add to ActionLog so the Evening Summary sees the resolution
                        action_text = f"Resolved blocker: {b.reason} (Auto-resolved because task '{task.title}' moved to {new_status_lower})"
                        self.db.add(StandupActionLog(update_id=update_id, action_taken=action_text))

                # Action log (prevent duplicates)
                label_str = f"[Task {task.label}] " if task.label else ""
                action_text = f"Updated task {label_str}{task.title} status to {new_status_lower}"
                existing_action = self.db.query(StandupActionLog).filter(
                    StandupActionLog.update_id == update_id,
                    StandupActionLog.action_taken == action_text
                ).first()
                
                if not existing_action:
                    action_log = StandupActionLog(
                        update_id=update_id,
                        action_taken=action_text
                    )
                    self.db.add(action_log)
                    self.db.flush() # Ensure visible to subsequent loops or AI parsing (autoflush=False)
            except Exception as e:
                logger.error(f"Error applying update for task {getattr(up, 'task_title', 'unknown')}: {e}")
                
        # Handle blockers (Update/Create and Auto-Resolution)
        standup_update = self.db.query(StandupUpdate).get(update_id)
        standup = self.db.query(Standup).get(standup_update.standup_id)
        
        # Fetch currently active blockers for this user in this project
        existing_active_blockers = self.db.query(Blocker).filter(
            Blocker.project_id == standup.project_id,
            Blocker.user_id == standup_update.user_id,
            Blocker.resolved_at.is_(None)
        ).all()
        
        reported_new_blocker_ids = []
        
        if parsed.blockers:
            for blk in parsed.blockers:
                try:
                    # Check if this is an update to an existing blocker (same task or same reason)
                    target_task_id = uuid.UUID(blk.task_id) if blk.task_id and blk.task_id != "null" else None
                    
                    # If label is provided but no task_id, resolve the task_id
                    if not target_task_id and hasattr(blk, 'task_label') and blk.task_label:
                        t = self.db.query(Task).filter(
                            Task.project_id == standup.project_id,
                            Task.label == blk.task_label,
                            Task.deleted_at.is_(None)
                        ).first()
                        if t:
                            target_task_id = t.id
                            logger.info(f"Resolved blocker task via label {blk.task_label} (ID: {target_task_id})")
                    
                    matched_blocker = None
                    ignore_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by", "with", "from", "blocked", "resolved", "fixed", "no", "longer", "issue"}
                    
                    for eb in existing_active_blockers:
                        # 1. Match by task_id
                        if target_task_id and eb.task_id == target_task_id:
                            matched_blocker = eb
                            break
                        
                        # 2. Match by exact reason or keyword overlap (for non-task blockers)
                        if not target_task_id and eb.task_id is None:
                            if eb.reason == blk.reason:
                                matched_blocker = eb
                                break
                            
                            res_words = set(re.findall(r'\w+', blk.reason.lower())) - ignore_words
                            eb_words = set(re.findall(r'\w+', eb.reason.lower())) - ignore_words
                            if res_words and eb_words and res_words.intersection(eb_words):
                                matched_blocker = eb
                                break
                    
                    if matched_blocker:
                        # Update existing blocker
                        matched_blocker.reason = blk.reason
                        matched_blocker.blocked_by = blk.blocked_by
                        matched_blocker.impact = blk.impact
                        reported_new_blocker_ids.append(matched_blocker.id)
                        logger.info(f"Updated existing blocker {matched_blocker.id}.")
                    else:
                        # Save as a new persistent blocker
                        new_blocker = Blocker(
                            project_id=standup.project_id,
                            user_id=standup_update.user_id,
                            task_id=target_task_id,
                            reason=blk.reason,
                            blocked_by=blk.blocked_by,
                            impact=blk.impact
                        )
                        self.db.add(new_blocker)
                        self.db.flush()
                        reported_new_blocker_ids.append(new_blocker.id)
                        
                        # Update task status to blocked if task_id provided
                        if target_task_id:
                            task = self.db.query(Task).get(target_task_id)
                            if task:
                                task.status = TaskStatus.BLOCKED
                                logger.info(f"Task {task.title} marked as BLOCKED due to persistent blocker entry.")
                    
                    # Format a professional, intelligent blocker message for action log (legacy support)
                    by_info = f" by {blk.blocked_by}" if blk.blocked_by else ""
                    # Resolve task label for the log if possible
                    label_str = ""
                    if blk.task_label:
                        label_str = f" in [Task {blk.task_label}]"
                    elif target_task_id:
                        t_lbl = self.db.query(Task.label).filter(Task.id == target_task_id).scalar()
                        if t_lbl:
                            label_str = f" in [Task {t_lbl}]"
                    
                    action_text = f"BLOCKER ({blk.type}): Blocked{by_info}{label_str} due to: {blk.reason}. Impact: {blk.impact}."
                    
                    existing_action = self.db.query(StandupActionLog).filter(
                        StandupActionLog.update_id == update_id,
                        StandupActionLog.action_taken == action_text
                    ).first()
                    if not existing_action:
                        action_log = StandupActionLog(
                            update_id=update_id,
                            action_taken=action_text
                        )
                        self.db.add(action_log)
                except Exception as e:
                    logger.error(f"Error applying blocker update: {e}")

        # --- REFINED RESOLUTION LOGIC ---
        # Resolution Loop:
        # 1. If a blocker is linked to a task, it's already auto-resolved when status changes to 'inprogress/completed' (handled earlier).
        # 2. For general (non-task) blockers, we NO LONGER resolve by omission. 
        #    They ONLY resolve if explicitly mentioned in parsed.resolved_blockers.
        
        # Explicitly resolved blockers from AI Agent
        if hasattr(parsed, 'resolved_blockers') and parsed.resolved_blockers:
            ignore_words = {
                "the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by", "with", "from", 
                "blocked", "resolved", "fixed", "no", "longer", "issue", "waiting", "proceed", "work"
            }
            
            for res in parsed.resolved_blockers:
                matched_db_blocker = None
                
                # 1. Try to match by label if provided (Search project-wide)
                if res.task_label:
                    matched_db_blocker = self.db.query(Blocker).join(Task).filter(
                        Blocker.project_id == standup.project_id,
                        Task.label == res.task_label,
                        Blocker.resolved_at.is_(None)
                    ).first()
                            
                # 2. If no label match, try BEST keyword match on reason (Current user only for safety)
                if not matched_db_blocker and res.reason:
                    res_words = set(re.findall(r'\w+', res.reason.lower())) - ignore_words
                    if res_words:
                        best_match = None
                        highest_intersection = 0
                        
                        for eb in existing_active_blockers:
                            eb_words = set(re.findall(r'\w+', eb.reason.lower())) - ignore_words
                            intersection = len(eb_words.intersection(res_words))
                            if intersection > highest_intersection:
                                highest_intersection = intersection
                                best_match = eb
                        
                        if best_match:
                            matched_db_blocker = best_match
                    
                    # 3. Smart Fallback: If no keyword match found but user has only 1 active blocker
                    if not matched_db_blocker and len(existing_active_blockers) == 1:
                        matched_db_blocker = existing_active_blockers[0]
                        logger.info(f"Smart Match: Resolving only active blocker {matched_db_blocker.id} based on generic resolution reply.")

                if matched_db_blocker:
                    matched_db_blocker.resolved_at = datetime.now(timezone.utc)
                    logger.info(f"Explicitly resolved blocker {matched_db_blocker.id} ('{matched_db_blocker.reason}') based on structured match.")
                    
                    # Action log for summary visibility
                    action_text = f"RESOLVED BLOCKER: {matched_db_blocker.reason}"
                    existing_action = self.db.query(StandupActionLog).filter(
                        StandupActionLog.update_id == update_id,
                        StandupActionLog.action_taken == action_text
                    ).first()
                    if not existing_action:
                        action_log = StandupActionLog(
                            update_id=update_id,
                            action_taken=action_text
                        )
                        self.db.add(action_log)

                    # Smart Task Recovery:
                    if matched_db_blocker.task_id:
                        other_blockers = self.db.query(Blocker).filter(
                            Blocker.task_id == matched_db_blocker.task_id,
                            Blocker.id != matched_db_blocker.id,
                            Blocker.resolved_at.is_(None)
                        ).count()
                        
                        if other_blockers == 0:
                            target_task = self.db.query(Task).get(matched_db_blocker.task_id)
                            if target_task and target_task.status == TaskStatus.BLOCKED:
                                target_task.status = TaskStatus.IN_PROGRESS
                                logger.info(f"Auto-restored task {target_task.title} to IN_PROGRESS after blocker resolution.")
        
        # Note: We removed the loop that resolved anything NOT in reported_new_blocker_ids.
        # This fulfills the user's request: "until and unless if explicitly mentioned... we cannot assume resolved".

        # Handle sentiment
        if parsed.sentiment == "at_risk":
            try:
                action_text = "SENTIMENT ALERT: Developer update indicates project risk."
                existing_action = self.db.query(StandupActionLog).filter(
                    StandupActionLog.update_id == update_id,
                    StandupActionLog.action_taken == action_text
                ).first()
                if not existing_action:
                    action_log = StandupActionLog(
                        update_id=update_id,
                        action_taken=action_text
                    )
                    self.db.add(action_log)
            except Exception as e:
                logger.error(f"Error applying sentiment alert: {e}")

        # Handle documentation updates
        if parsed.doc_updates:
            # Fetch standup to get project_id
            standup_update = self.db.query(StandupUpdate).get(update_id)
            standup = self.db.query(Standup).get(standup_update.standup_id)

            for doc_up in parsed.doc_updates:
                try:
                    # Find document WITHIN this project
                    doc = (
                        self.db.query(Document)
                        .filter(
                            Document.project_id == standup.project_id,
                            Document.title.ilike(doc_up.title),
                            Document.deleted_at.is_(None),
                        )
                        .first()
                    )

                    is_new = False
                    if not doc:
                        # Restore soft-deleted doc if it exists, otherwise create a new one.
                        deleted_doc = (
                            self.db.query(Document)
                            .filter(
                                Document.project_id == standup.project_id,
                                Document.title.ilike(doc_up.title),
                                Document.deleted_at.isnot(None),
                            )
                            .first()
                        )
                        if deleted_doc:
                            is_new = True
                            doc = deleted_doc
                            doc.deleted_at = None
                            self.db.add(doc)
                        else:
                            # Create new document if not found in this project
                            is_new = True
                            doc = Document(
                                project_id=standup.project_id,
                                title=doc_up.title,
                                created_by=standup_update.user_id,
                            )
                            self.db.add(doc)
                            self.db.flush()

                    # Append new information as a new block at the end
                    last_block = (
                        self.db.query(DocumentBlock)
                        .filter(DocumentBlock.doc_id == doc.id)
                        .order_by(DocumentBlock.position_key.desc())
                        .first()
                    )

                    next_pos = str(int(last_block.position_key) + 1).zfill(3) if last_block else "001"

                    new_block = DocumentBlock(
                        doc_id=doc.id,
                        content=doc_up.content,
                        position_key=next_pos,
                        type="paragraph",
                        last_edited_by=standup_update.user_id,
                    )
                    self.db.add(new_block)

                    prefix = "CREATED NEW DOCUMENT" if is_new else "UPDATED DOCUMENT"
                    action_text = f"{prefix}: {doc_up.title} with new info."
                    existing_action = self.db.query(StandupActionLog).filter(
                        StandupActionLog.update_id == update_id,
                        StandupActionLog.action_taken == action_text,
                    ).first()
                    if not existing_action:
                        action_log = StandupActionLog(
                            update_id=update_id,
                            action_taken=action_text,
                        )
                        self.db.add(action_log)
                except Exception as e:
                    logger.error(f"Error applying doc update {doc_up.title}: {e}")

        # Handle new tasks
        if parsed.new_tasks:
            # Fetch standup to get project_id
            standup_update = self.db.query(StandupUpdate).get(update_id)
            standup = self.db.query(Standup).get(standup_update.standup_id)
            
            for new_t in parsed.new_tasks:
                try:
                    target_member_id = None
                    
                    if new_t.assignee:
                        # Try to find user by name in this project
                        member = self.db.query(ProjectMember).join(User).filter(
                            ProjectMember.project_id == standup.project_id,
                            User.name.ilike(new_t.assignee)
                        ).first()
                        
                        if member:
                            target_member_id = member.id
                        else:
                            logger.warning(f"Could not find member matching name: {new_t.assignee}")
                    
                    # If no assignee found or mentioned, assign to the person replying
                    if not target_member_id:
                        member = self.db.query(ProjectMember).filter(
                            ProjectMember.project_id == standup.project_id,
                            ProjectMember.user_id == standup_update.user_id
                        ).first()
                        if member:
                            target_member_id = member.id
                    
                    if target_member_id:
                        logger.info(f"Creating new task '{new_t.title}' with deadline string: '{new_t.deadline}'")
                        parsed_deadline = self._parse_deadline(new_t.deadline)
                        if parsed_deadline:
                            logger.info(f"Parsed datetime for new task: {parsed_deadline}")
                        default_deadline = None
                        if not parsed_deadline:
                            # Ensure AI-created tasks always have a concrete deadline in the DB.
                            default_deadline = datetime.now(timezone.utc) + timedelta(days=7)
                        
                        status_obj = self._safe_status_conversion(new_t.status)
                        
                        # Deduplication check
                        existing_task = self._find_existing_task(standup.project_id, new_t.title, target_member_id)
                        
                        if existing_task:
                            logger.info(f"Deduplication: Task '{new_t.title}' already exists. Updating status.")
                            new_task_obj = existing_task
                            new_task_obj.status = status_obj
                            if parsed_deadline:
                                new_task_obj.deadline = parsed_deadline
                            elif default_deadline and new_task_obj.deadline is None:
                                new_task_obj.deadline = default_deadline
                        else:
                            new_task_obj = Task(
                                title=new_t.title,
                                project_id=standup.project_id,
                                description=new_t.description or f"Created via StandUp Agent from reply: {new_t.title}",
                                status=status_obj,
                                project_member_id=target_member_id,
                                deadline=parsed_deadline or default_deadline,
                                complexity=new_t.complexity,
                            )
                            # If deadline couldn't be parsed into a date, append it to description
                            if new_t.deadline and not parsed_deadline:
                                new_task_obj.description += f" (Deadline: {new_t.deadline})"
                            self.db.add(new_task_obj)
                        self.db.flush() # Get ID for the log
                        
                        # Create TaskLog for new task
                        log_entry = f"Task created via StandUp Agent. Description: {new_task_obj.description}"
                        if new_t.deadline:
                            log_entry += f" Deadline: {new_t.deadline}"
                        elif default_deadline:
                            log_entry += f" Deadline: {default_deadline.strftime('%Y-%m-%d')} (default)"
                        if new_t.complexity:
                            log_entry += f" Complexity: {new_t.complexity}"
                        task_log = TaskLog(task_id=new_task_obj.id, log=log_entry)
                        self.db.add(task_log)


                        # Avoid noisy "to self" in logs; self-assignment is implied.
                        assignee_str = f" to {new_t.assignee}" if new_t.assignee else ""
                        label_str = f"[Task {new_task_obj.label}] " if new_task_obj.label else ""
                        # Use "CREATED NEW TASK: " prefix to ensure correct summary phrasing
                        action_text = f"CREATED NEW TASK: {label_str}{new_t.title}{assignee_str}"
                        existing_action = self.db.query(StandupActionLog).filter(
                            StandupActionLog.update_id == update_id,
                            StandupActionLog.action_taken == action_text
                        ).first()
                        if not existing_action:
                            action_log = StandupActionLog(
                                update_id=update_id,
                                action_taken=action_text
                            )
                            self.db.add(action_log)
                    else:
                        logger.error(f"Failed to find a valid project member to assign task: {new_t.title}")
                except Exception as e:
                    logger.error(f"Error applying new task creation for {new_t.title}: {e}")


    def _activate_selected_task(self, task: Task, member: ProjectMember) -> Optional[Task]:
        """Assign and activate a TODO task for the member. Returns task if successful, None otherwise."""
        # Only act on TODO tasks
        if task.status != TaskStatus.TODO:
            logger.info(f"Task-selection: Task {task.label} is already {task.status.value}, skipping")
            return None
        # Assign if unassigned
        if task.project_member_id is None:
            task.project_member_id = member.id
            logger.info(f"Task-selection: Assigned task {task.label} to member {member.id}")
        task.status = TaskStatus.IN_PROGRESS
        logger.info(f"Task-selection: Updated task {task.label} to in_progress")
        self.db.add(TaskLog(
            task_id=task.id,
            log="Status: in_progress. Task selected by member during standup reply. (via StandUp Agent)"
        ))
        self.db.flush()
        return task

    def _detect_task_selection(
        self,
        reply_text: str,
        member: ProjectMember,
        standup: Standup,
    ) -> Optional[Task]:
        """
        Detects if the reply is selecting a suggested (TODO) task and immediately
        updates that task to IN_PROGRESS in the DB.

        Returns the Task object if a selection was detected, otherwise None.
        The caller is responsible for creating the StandupActionLog once the
        StandupUpdate record has been saved.

        Two matching strategies:
        1. Label-based: "I am doing task 13", "I will be going with task 2", etc.
        2. Name-based: "I'll take the API integration task" (keyword matching)
        """
        # ---------------------------------------------------------------
        # PASS 1: Label-based matching — task N  
        # ---------------------------------------------------------------
        action_words = (
            r"do|doing|take|taking|going\s+with|be\s+going\s+with|working\s+on|work\s+on|"
            r"pick(?:ing)?\s+up|start(?:ing)?|handle|handling|proceeding\s+with|"
            r"choosing|opting\s+for|will\s+work\s+on|would\s+work\s+on|"
            r"going\s+to\s+do|going\s+to\s+take|going\s+to\s+work\s+on|going\s+to\s+handle|"
            r"would\s+like\s+to\s+(?:do|take|work\s+on)"
        )
        label_pattern = re.compile(
            rf"(?:i(?:'m|'ll|\s+am|\s+will|\s+would)?\s+(?:am\s+|going\s+to\s+|be\s+going\s+|'ll\s+)?(?:{action_words})"
            rf"|taking|picking\s+up)\s+task\s+(\d+)",
            re.IGNORECASE
        )
        match = label_pattern.search(reply_text)
        if match:
            task_label = int(match.group(1))
            logger.info(f"Task-selection (label match): label={task_label} by member {member.id}")
            task = self.db.query(Task).filter(
                Task.project_id == standup.project_id,
                Task.label == task_label,
                Task.status == TaskStatus.TODO,
                Task.deleted_at.is_(None)
            ).first()
            if task:
                return self._activate_selected_task(task, member)
            logger.warning(f"Task-selection: Task {task_label} not found or not TODO in project {standup.project_id}")

        # ---------------------------------------------------------------
        # PASS 2: Name-based matching — keyword overlap with task titles
        # ---------------------------------------------------------------
        todo_tasks = self.db.query(Task).filter(
            Task.project_id == standup.project_id,
            Task.status == TaskStatus.TODO,
            Task.deleted_at.is_(None)
        ).all()

        reply_lower = reply_text.lower()
        best_task = None
        best_score = 0.0

        for t in todo_tasks:
            if not t.title:
                continue
            # Split title into meaningful words (length > 3 to skip "API", "the", etc.)
            title_words = [w for w in re.split(r'\W+', t.title.lower()) if len(w) > 3]
            if not title_words:
                continue
            matched = sum(1 for w in title_words if w in reply_lower)
            score = matched / len(title_words)
            # Require at least 50% of significant title words to appear in the reply
            if score > best_score and score >= 0.5:
                best_score = score
                best_task = t

        if best_task:
            logger.info(f"Task-selection (name match): '{best_task.title}' score={best_score:.2f} by member {member.id}")
            return self._activate_selected_task(best_task, member)

        return None

    def _log_task_selection_action(self, update_id: uuid.UUID, task: Task):
        """
        Creates a StandupActionLog entry for a task that was selected from suggestions.
        This makes the selection visible in the standup summary.
        """
        label_str = f"[Task {task.label}] " if task.label else ""
        action_text = f"Updated task {label_str}{task.title} status to in_progress"

        # Avoid duplicates
        existing = self.db.query(StandupActionLog).filter(
            StandupActionLog.update_id == update_id,
            StandupActionLog.action_taken == action_text
        ).first()
        if not existing:
            self.db.add(StandupActionLog(
                update_id=update_id,
                action_taken=action_text
            ))
            self.db.flush() # Ensure visible to subsequent queries in same session (autoflush=False)
            logger.info(f"Task-selection: Created action log for task {task.label}")



    def _find_existing_task(self, project_id: uuid.UUID, title: str, member_id: Optional[uuid.UUID]) -> Optional[Task]:
        """
        Looks for an existing active task by title within a project, assigned to a specific member.
        Strict matching on project and member to avoid cross-assignment accidental updates.
        """
        if not title or not member_id:
            return None
            
        return self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.project_member_id == member_id,
            Task.title.ilike(title.strip()),
            Task.deleted_at.is_(None)
        ).first()

    def _parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """
        Attempts to parse a deadline string into a datetime object.
        Returns None if parsing fails or if the string is just 'null'.
        """
        if not deadline_str or deadline_str == "null":
            return None
        
        if not date_parser:
            logger.error("CRITICAL: dateutil.parser is None! Falling back to isoformat.")
            # Fallback if dateutil is missing
            try:
                return datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            except Exception:
                return None
                
        try:
            # fuzzy=True allows handling strings with extra words like 'by Friday'
            # Use current datetime as default for relative dates like "Friday"
            dt = date_parser.parse(deadline_str, fuzzy=True, default=datetime.now())
            # Make sure it's timezone-aware for the DB column (timestamp with time zone)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            logger.info(f"SUCCESS: Parsed '{deadline_str}' into {dt}")
            return dt
        except Exception as e:
            logger.error(f"FAILURE: Could not parse '{deadline_str}' even with fuzzy logic: {e}")
            return None
    def finalize_all_active_standups(self):
        """
        Finds all standups created in the last 24 hours that are not yet finalized and finalizes them.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Find recent unfinalized standups
        standups = self.db.query(Standup).filter(
            Standup.created_at >= cutoff,
            Standup.summary.is_(None),
            Standup.deleted_at.is_(None)
        ).all()
        
        logger.info(f"Summary: Found {len(standups)} unfinalized standups in the last 24 hours.")
        
        results = []
        for standup in standups:
            try:
                # 1. Catch any remaining replies
                self.process_new_replies(str(standup.id))
                # 2. Finalize (posts to Slack and sets .summary)
                self.finalize_standup(str(standup.id))
                results.append(str(standup.id))
            except Exception as e:
                logger.error(f"Failed to auto-finalize standup {standup.id}: {e}")
        
        return results

    def finalize_standup(self, standup_id: str):
        """
        Gathers all updates and blockers for a standup and posts a comprehensive summary to Slack.
        """
        try:
            standup_uuid = uuid.UUID(standup_id) if isinstance(standup_id, str) else standup_id
        except ValueError:
            logger.error(f"Invalid standup_id format: {standup_id}")
            raise ValueError(f"Invalid standup_id format: {standup_id}")
        
        standup = self.db.query(Standup).filter(Standup.id == standup_uuid).first()
        if not standup:
            logger.error(f"Standup {standup_id} not found for finalization")
            raise ValueError(f"Standup {standup_id} not found")

        logger.info(f"Finalizing standup {standup_id} for project {standup.project_id}")

        # 1. Fetch all updates for this standup
        updates = self.db.query(StandupUpdate).filter(
            StandupUpdate.standup_id == standup.id,
            StandupUpdate.deleted_at.is_(None)
        ).all()
        
        # 2. Extract structured summary data from logs
        summary_updates = []
        seen_updates = set()  # To prevent duplicates in the summary
        session_blockers = []
        session_insights = []
        
        for up in updates:
            user = self.db.query(User).get(up.user_id)
            user_name = user.name if user else "Unknown"
            
            action_logs = self.db.query(StandupActionLog).filter(StandupActionLog.update_id == up.id).all()
            for log in action_logs:
                # Handle standard status updates
                if "Updated task" in log.action_taken:
                    parts = log.action_taken.split("Updated task ")[1].split(" status to ")
                    task_name = parts[0]
                    status = parts[1]
                    update_key = (user_name, task_name, status)
                    if update_key not in seen_updates:
                        summary_updates.append({"user": user_name, "task": task_name, "status": status})
                        seen_updates.add(update_key)
                
                # Handle persistent blockers reported in this session
                elif "BLOCKER (" in log.action_taken:
                    blocker_detail = log.action_taken.split(": ", 1)[1]
                    session_blockers.append(f"{user_name}: {blocker_detail}")
                
                # Handle resolved blockers
                elif "RESOLVED BLOCKER: " in log.action_taken:
                    resolved_msg = log.action_taken.split("RESOLVED BLOCKER: ")[1]
                    update_key = (user_name, f"blocker: {resolved_msg}", "resolved")
                    if update_key not in seen_updates:
                        summary_updates.append({"user": user_name, "task": f"blocker: {resolved_msg}", "status": "resolved"})
                        seen_updates.add(update_key)
                
                # Handle sentiment alerts
                elif "SENTIMENT ALERT: " in log.action_taken:
                    session_insights.append(f"Risk Warning: {user_name}'s update suggests project risk.")
                
                # Handle newly created tasks or direct status reports
                elif any(prefix in log.action_taken for prefix in ["CREATED NEW TASK", "TODO: ", "IN_PROGRESS: ", "COMPLETED: ", "BLOCKED: "]):
                    task_part = ""
                    status = "newly created"
                    
                    if "CREATED NEW TASK" in log.action_taken:
                        status = "newly created"
                        # Extract task part: e.g. "CREATED NEW TASK: [Task 11] Title to Akshita"
                        task_part = log.action_taken.replace("CREATED NEW TASK: ", "").strip()
                    else:
                        for prefix in ["TODO: ", "IN_PROGRESS: ", "COMPLETED: ", "BLOCKED: "]:
                            if log.action_taken.startswith(prefix):
                                task_part = log.action_taken.split(prefix, 1)[1]
                                status = prefix.replace(": ", "").lower()
                                break
                    
                    if task_part:
                        update_key = (user_name, task_part, status)
                        if update_key not in seen_updates:
                            summary_updates.append({"user": user_name, "task": task_part, "status": status})
                            seen_updates.add(update_key)

                # Handle documentation updates
                elif any(prefix in log.action_taken for prefix in ["CREATED NEW DOCUMENT: ", "UPDATED DOCUMENT: "]):
                    if "CREATED NEW DOCUMENT: " in log.action_taken:
                        doc_title = log.action_taken.split("CREATED NEW DOCUMENT: ")[1].split(" with new info.")[0]
                        status = "document_create"
                    else:
                        doc_title = log.action_taken.split("UPDATED DOCUMENT: ")[1].split(" with new info.")[0]
                        status = "document_update"
                    
                    update_key = (user_name, doc_title, status)
                    if update_key not in seen_updates:
                        summary_updates.append({"user": user_name, "task": doc_title, "status": status})
                        seen_updates.add(update_key)

        # 3. Gather ALL currently unresolved blockers for the whole project
        from src.backend.model.blocker import Blocker as DBBlocker
        all_active_blockers_db = self.db.query(DBBlocker).filter(
            DBBlocker.project_id == standup.project_id,
            DBBlocker.resolved_at.is_(None)
        ).all()
        
        all_active_blockers = []
        for b in all_active_blockers_db:
            u = self.db.query(User).get(b.user_id)
            t_label = b.task.label if b.task else None
            all_active_blockers.append({
                "user": u.name if u else "Unknown",
                "reason": b.reason,
                "label": t_label
            })

        # 4. Generate the final summary message
        from src.backend.model.project import Project
        project = self.db.query(Project).get(standup.project_id)
        project_name = project.name if project else "Project"
        
        summary_text = self.generator.generate_standup_summary(
            project_name, 
            summary_updates, 
            session_blockers,
            all_active_blockers=all_active_blockers,
            insights=session_insights
        )
        
        # 5. Post to Slack in the same thread
        try:
            self.slack_service.post_message(
                standup.slack_channel_id,
                summary_text,
                thread_ts=standup.message_ts
            )
            
            # 6. Mark standup as summarized
            standup.summary = summary_text
            self.db.commit()
            logger.info(f"Finalized standup {standup_id} with summary.")
        except Exception as e:
            logger.error(f"Failed to post summary for standup {standup_id}: {e}", exc_info=True)
            self.db.rollback()
            raise Exception(f"Failed to post summary to Slack: {e}")

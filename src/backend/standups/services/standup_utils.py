import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

from src.backend.model.task import Task, TaskStatus, TaskPriority, TaskComplexity
from src.backend.model.project import ProjectMember
from src.backend.model.standup import Standup
from src.backend.model.task_log import TaskLog
from src.backend.model.standup_action_log import StandupActionLog

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

logger = logging.getLogger(__name__)

class StandupUtils:
    @staticmethod
    def safe_status_conversion(status_str: str, default: TaskStatus = TaskStatus.TODO) -> TaskStatus:
        """Safely converts a string to TaskStatus enum."""
        if not status_str:
            return default
        try:
            return TaskStatus(status_str.lower().replace(" ", "_"))
        except ValueError:
            logger.warning(f"Unknown task status: '{status_str}'. Defaulting to {default.value}")
            return default

    @staticmethod
    def safe_priority_conversion(priority_str: str, default: TaskPriority = TaskPriority.MEDIUM) -> TaskPriority:
        """Safely converts a string to TaskPriority enum."""
        if not priority_str:
            return default
        try:
            return TaskPriority(priority_str.lower())
        except ValueError:
            return default

    @staticmethod
    def safe_complexity_conversion(complexity_str: str, default: TaskComplexity = TaskComplexity.MEDIUM) -> TaskComplexity:
        """Safely converts a string to TaskComplexity enum."""
        if not complexity_str:
            return default
        try:
            return TaskComplexity(complexity_str.lower())
        except ValueError:
            return default

    @staticmethod
    def parse_deadline(deadline_str: str) -> Optional[datetime]:
        """
        Attempts to parse a deadline string into a datetime object.
        """
        if not deadline_str or deadline_str == "null":
            return None
        
        if not date_parser:
            logger.error("CRITICAL: dateutil.parser is None! Falling back to isoformat.")
            try:
                dt = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return None
                
        try:
            dt = date_parser.parse(deadline_str, fuzzy=True, default=datetime.now())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception as e:
            logger.error(f"Could not parse '{deadline_str}': {e}")
            return None

    @staticmethod
    def parse_blocker_action(action_text: str) -> dict:
        """Parses a BLOCKER action log entry into structured details."""
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

    @staticmethod
    def extract_new_task_name(action_text: str, user_name: str) -> Optional[str]:
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

    @staticmethod
    def find_existing_task(db: Session, project_id: uuid.UUID, title: str, member_id: Optional[uuid.UUID]) -> Optional[Task]:
        """
        Finds a task by project, title, and member. 
        If member_id is provided, checks for tasks assigned to them first.
        If no match is found, checks for unassigned tasks with the same title.
        """
        if not title:
            return None
            
        # 1. Try finding task assigned to this member
        if member_id:
            task = db.query(Task).filter(
                Task.project_id == project_id,
                Task.project_member_id == member_id,
                Task.title.ilike(title.strip()),
                Task.deleted_at.is_(None)
            ).first()
            if task:
                return task

        # 2. Try finding unassigned task with the same title
        return db.query(Task).filter(
            Task.project_id == project_id,
            Task.project_member_id.is_(None),
            Task.title.ilike(title.strip()),
            Task.deleted_at.is_(None)
        ).first()

    @staticmethod
    def detect_task_selection(db: Session, reply_text: str, member: ProjectMember, project_id: uuid.UUID) -> Optional[Task]:
        """Detects if the reply is selecting a suggested task."""
        reply_lower = reply_text.lower()
        
        action_words = (
            r"do|doing|take|taking|going\s+with|be\s+going\s+with|working\s+on|work\s+on|"
            r"pick(?:ing)?\s+up|start(?:ing)?|handle|handling|proceeding\s+with|"
            r"choosing|opting\s+for|will\s+work\s+on|would\s+work\s+on|"
            r"will\s+take|can\s+take|could\s+take|"
            r"going\s+to\s+do|going\s+to\s+take|going\s+to\s+work\s+on|going\s+to\s+handle|"
            r"would\s+like\s+to\s+(?:do|take|work\s+on)"
        )
        label_pattern = re.compile(
            rf"(?:i(?:'m|'ll|\s+am|\s+will|\s+would|\s+can|\s+could)?\s+(?:am\s+|going\s+to\s+|be\s+going\s+|'ll\s+)?(?:{action_words})"
            rf"|taking|picking\s+up)\s+task\s+(\d+)",
            re.IGNORECASE
        )
        match = label_pattern.search(reply_text)
        if match:
            task_label = int(match.group(1))
            task = db.query(Task).filter(
                Task.project_id == project_id,
                Task.label == task_label,
                Task.status == TaskStatus.TODO,
                Task.deleted_at.is_(None)
            ).first()
            if task:
                return StandupUtils.activate_selected_task(db, task, member)

        # Keyword matching fallback - only if selection intent is detected
        selection_intent_patterns = [
            r"i('m|'ll| am| will)? (take|taking|pick|start|work on|handle)",
            r"going to (do|take|work on|handle)",
            r"picking up",
            r"would like to (do|take|work on)"
        ]
        has_selection_intent = any(re.search(p, reply_lower) for p in selection_intent_patterns)
        
        if not has_selection_intent:
            return None

        todo_tasks = db.query(Task).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.TODO,
            Task.deleted_at.is_(None)
        ).all()

        best_task = None
        best_score = 0.0
        stop_words = {"task", "project", "issue", "ticket"}

        for t in todo_tasks:
            if not t.title: continue
            title_words = [w for w in re.split(r'\W+', t.title.lower()) if len(w) > 3 and w not in stop_words]
            if not title_words: continue
            matched = sum(1 for w in title_words if w in reply_lower)
            score = matched / len(title_words)
            if score > best_score and score >= 0.5:
                best_score = score
                best_task = t

        if best_task:
            return StandupUtils.activate_selected_task(db, best_task, member)
        return None

    @staticmethod
    def activate_selected_task(db: Session, task: Task, member: ProjectMember) -> Task:
        if task.project_member_id is None:
            task.project_member_id = member.id
        task.status = TaskStatus.IN_PROGRESS
        db.add(TaskLog(
            task_id=task.id,
            log="Status: in_progress. Task selected by member during standup reply. (via StandUp Agent)"
        ))
        db.flush()
        return task

    @staticmethod
    def log_task_selection_action(db: Session, update_id: uuid.UUID, task: Task):
        label_str = f"[Task {task.label}] " if task.label else ""
        action_text = f"Updated task {label_str}{task.title} status to in_progress"
        existing = db.query(StandupActionLog).filter(
            StandupActionLog.update_id == update_id,
            StandupActionLog.action_taken == action_text
        ).first()
        if not existing:
            db.add(StandupActionLog(update_id=update_id, action_taken=action_text))
            db.flush()

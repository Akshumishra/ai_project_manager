import logging
import re

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from src.backend.model.task import Task, TaskStatus
from src.backend.model.project import ProjectMember, Project
from src.backend.model.user import User
from src.backend.model.blocker import Blocker
from src.backend.model.task_log import TaskLog
from datetime import datetime, timezone
from src.backend.config import settings

logger = logging.getLogger(__name__)

class StandupGenerator:
    def __init__(self, db: Session):
        self.db = db

    def _strip_to_self(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return text
        cleaned = re.sub(r"\s+to\s+self\b", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        return cleaned

    def _is_meaningful_blocker_reason(self, reason: Optional[str], blocked_by: Optional[str]) -> bool:
        if not reason:
            return False
        reason_norm = reason.strip()
        if not reason_norm:
            return False

        reason_l = reason_norm.lower().strip().rstrip(".")
        if reason_l in {"n/a", "na", "none", "unknown"}:
            return False
        if "did not specify the reason" in reason_l or "reason not specified" in reason_l or "no reason provided" in reason_l:
            return False

        blocked_by_l = (blocked_by or "").strip().lower().strip().rstrip(".")
        if blocked_by_l:
            if reason_l == f"blocked by {blocked_by_l}":
                return False

        if reason_l.startswith("blocked by ") and ("due to" not in reason_l) and ("because" not in reason_l):
            if re.fullmatch(r"blocked by [^,.:;!?\\n-]+", reason_l):
                after_words = reason_l.removeprefix("blocked by ").split()
                if len(after_words) <= 3:
                    return False

        return True

    def _should_show_blocked_by(self, member: str, blocked_by: Optional[str]) -> bool:
        if not blocked_by:
            return False
        blocked_by_norm = blocked_by.strip()
        if not blocked_by_norm:
            return False

        blocked_by_l = blocked_by_norm.lower().strip().rstrip(".")
        if blocked_by_l in {"n/a", "na", "none", "unknown", "self", "me", "myself"}:
            return False
        if member and blocked_by_l == member.lower():
            return False
        return True
    
    def _format_task_link(self, label: Optional[int], task_id: Optional[str] = None, project_id: Optional[str] = None) -> str:
        """Formats a task label as a clickable Slack link (<url|text>)."""
        if label is None:
            return ""
        
        # Prefer deep link to task detail if we have the IDs
        if task_id and project_id:
            url = f"{settings.BASE_TASK_URL}/project/{project_id}/task/{task_id}"
        else:
            # Fallback for when we only have the label
            url = f"{settings.BASE_TASK_URL}/tasks/{label}"
            
        return f"<{url}|Task {label}>"

    def _get_link_from_label(self, label: int, project_id: str) -> str:
        """Helper to resolve a task link when only the label and project_id are known."""
        task = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.label == label,
            Task.deleted_at.is_(None)
        ).first()
        
        if task:
            return self._format_task_link(label, str(task.id), str(project_id))
        return self._format_task_link(label)
    
    def get_idle_member_suggestions(self, project_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identifies members with no active tasks and finds potential TODO tasks to suggest.
        
        Returns:
            Dict mapping member names to a list of suggested task info.
        """
        from src.backend.model.project import ProjectMember
        
        members = self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
        suggestions = {}

        for member in members:
            active_count = self.db.query(Task).filter(
                Task.project_id == project_id,
                Task.project_member_id == member.id,
                Task.status == TaskStatus.IN_PROGRESS,
                Task.deleted_at.is_(None),
            ).count()
            
            if active_count > 0:
                continue

            personal_todos = self.db.query(Task).filter(
                Task.project_id == project_id,
                Task.project_member_id == member.id,
                Task.status == TaskStatus.TODO,
                Task.deleted_at.is_(None),
            ).order_by(Task.deadline.asc().nullslast(), Task.label.asc()).limit(3).all()

            unassigned_todos = []
            if len(personal_todos) < 3:
                unassigned_todos = self.db.query(Task).filter(
                    Task.project_id == project_id,
                    Task.project_member_id.is_(None),
                    Task.status == TaskStatus.TODO,
                    Task.deleted_at.is_(None),
                ).order_by(Task.deadline.asc().nullslast(), Task.label.asc()).limit(3 - len(personal_todos)).all()

            candidates = personal_todos + unassigned_todos
            if candidates:
                user = self.db.query(User).get(member.user_id)
                member_name = user.name if user else "Unknown"
                
                suggestions[member_name] = [
                    {
                        "id": str(t.id),
                        "title": t.title,
                        "label": t.label,
                        "status": "todo",
                        "description": t.description,
                        "complexity": t.complexity,
                        "deadline": t.deadline.strftime("%Y-%m-%d") if t.deadline else "No deadline",
                        "is_unassigned": t.project_member_id is None
                    } for t in candidates
                ]
        
        return suggestions

    def fetch_active_tasks(self, project_id: str) -> tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """
        Fetches active tasks for a project and groups them by developer.
        Also identifies suggestions for idle members.
        Returns a tuple of (grouped_tasks, overdue_tasks, suggestions).
        """
        # Get tasks that are either IN_PROGRESS or BLOCKED for this project
        # Note: we exclude TODO from grouped_tasks now because they will be in suggestions
        tasks = (
            self.db.query(Task)
            .filter(
                Task.project_id == project_id,
                Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]),
                Task.deleted_at.is_(None)
            )
            .all()
        )

        grouped_tasks = {}
        overdue_tasks = []
        now = datetime.now(timezone.utc)

        for task in tasks:
            if not task.project_member_id:
                continue
            member = self.db.query(ProjectMember).get(task.project_member_id)
            if not member:
                continue
                
            user = self.db.query(User).get(member.user_id)
            member_name = user.name if user else "Unknown"

            is_overdue = False
            deadline = getattr(task, 'deadline', None)
            if deadline:
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                if deadline < now:
                    is_overdue = True

            task_info = {
                "id": str(task.id),
                "title": task.title,
                "status": task.status.value,
                "description": task.description,
                "deadline": task.deadline.strftime("%Y-%m-%d") if task.deadline else None,
                "complexity": task.complexity,
                "label": task.label,
                "is_overdue": is_overdue,
                "assignee": member_name
            }

            if is_overdue:
                overdue_tasks.append(task_info)

            if member_name not in grouped_tasks:
                grouped_tasks[member_name] = []
            
            grouped_tasks[member_name].append(task_info)
            
        suggestions = self.get_idle_member_suggestions(project_id)
        
        return grouped_tasks, overdue_tasks, suggestions


    def fetch_active_blockers(self, project_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetches all unresolved blockers for a project, grouped by user.
        """
        blockers = (
            self.db.query(Blocker)
            .filter(
                Blocker.project_id == project_id,
                Blocker.resolved_at.is_(None)
            )
            .all()
        )
        
        grouped = {}
        for blk in blockers:
            user_name = blk.user.name if blk.user else "Unknown"
            if user_name not in grouped:
                grouped[user_name] = []
            
            grouped[user_name].append({
                "reason": blk.reason,
                "blocked_by": blk.blocked_by,
                "impact": blk.impact,
                "task_id": str(blk.task_id) if blk.task_id else None,
                "task_label": blk.task.label if blk.task else None
            })
        return grouped

    def generate_standup_prompt(
        self, 
        project_id: str,
        project_name: str, 
        grouped_tasks: Dict[str, List[Dict[str, Any]]],
        overdue_tasks: List[Dict[str, Any]] = None,
        suggestions: Dict[str, List[Dict[str, Any]]] = None,
        historical_highlights: Optional[Dict[str, Dict[str, Any]]] = None,
        active_blockers: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        missed_update_members: Optional[List[str]] = None,
        summary_insights: Optional[List[str]] = None
    ) -> str:
        """
        Generates the standard standup message for Slack with an optional historical context.
        """
        message = f"Good morning team! ☀️ Time for our daily standup for *{project_name}*.\n\n"
        
        # Section for members who missed the previous standup
        if missed_update_members:
            message += "📢 *Missed Updates Notice*\n"
            message += "The following members haven't provided an update for some time despite having active tasks. Looking forward to hearing from you today!\n"
            for member in missed_update_members:
                message += f"• *{member}*\n"
            message += "\n"
        
        if overdue_tasks:
            message += "🚨 *CRITICAL: Deadline Risks Identified*\n"
            message += "The following tasks have missed their deadlines and require urgent attention:\n"
            for t in overdue_tasks:
                link = self._format_task_link(t.get('label'), t.get('id'), project_id)
                message += f"• {link} *{t['title']}* (Assignee: {t['assignee']}, Deadline: {t['deadline']})\n"
            message += "\n"

        # 1. Dedicated Blocker Section (From persistent blockers table)
        if active_blockers:
            message += "🚧 *Current Member Blockers:*\n"
            for member, blockers in active_blockers.items():
                message += f"• *{member}*:\n"
                for blk in blockers:
                    task_link = ""
                    if blk['task_label']:
                        task_link = f" in {self._format_task_link(blk['task_label'], blk['task_id'], project_id)}"
                    reason = (blk.get("reason") or "").strip()
                    blocked_by = (blk.get("blocked_by") or "").strip()
                    impact = (blk.get("impact") or "").strip()

                    if self._is_meaningful_blocker_reason(reason, blocked_by):
                        message += f"    ⚠️ *Reason*: {reason}{task_link}\n"
                    else:
                        # Respect "no reason if missing" while still making each blocker visible in the prompt.
                        message += f"    ⚠️ *Blocker reported*{task_link}\n"

                    if self._should_show_blocked_by(member, blocked_by):
                        message += f"    • *Blocked By*: {blocked_by}\n"

                    if impact:
                        message += f"    • *Impact*: {impact}\n"
            message += "\n"

        if historical_highlights:
            # 2. Key Insights Section (Progress/Achievements Only)
            # Note: We now skip blockers here because they are pulled from the session-independent blockers table above.
            insight_content = ""
            for member, highlights in historical_highlights.items():
                summary = self._strip_to_self(highlights.get('summary'))
                # Filter out "No progress updates reported." and empty summaries
                if summary and summary not in ["No key update was reported.", "No progress updates reported."]:
                    # Format task links in summary
                    summary = re.sub(
                        r"(?i)\[?Task (\d+)\]?",
                        lambda m: self._get_link_from_label(int(m.group(1)), project_id),
                        summary
                    )
                    insight_content += f"• *{member}*: {summary}\n"

            if insight_content:
                message += "💡 *Key Insights from Last Standup:*\n"
                message += insight_content + "\n"

            new_task_entries = []
            seen_tasks = set()
            for member, highlights in historical_highlights.items():
                for task_name in highlights.get("new_tasks", []):
                    entry = (member, task_name)
                    if entry in seen_tasks:
                        continue
                    seen_tasks.add(entry)
                    new_task_entries.append(entry)

            if new_task_entries:
                message += "🆕 *Tasks Added Last Standup:*\n"
                for member, task_name in new_task_entries:
                    task_name_clean = self._strip_to_self(task_name) or task_name
                    task_name_clean = re.sub(
                        r"\[Task (\d+)\]",
                        lambda m: self._get_link_from_label(int(m.group(1)), project_id),
                        task_name_clean,
                    )
                    message += f"• *{member}*: {task_name_clean}\n"
                message += "\n"

        if summary_insights:
            message += "💡 *Insights from Last Standup:*\n"
            for insight in summary_insights:
                insight_clean = self._strip_to_self(insight)
                # Format task links in insight
                insight_clean = re.sub(
                    r"(?i)\[?Task (\d+)\]?",
                    lambda m: self._get_link_from_label(int(m.group(1)), project_id),
                    insight_clean
                )
                message += f"• {insight_clean}\n"
            message += "\n"

        blocked_tasks = self._collect_current_blocked_tasks(grouped_tasks)
        if blocked_tasks:
            message += "🚧 *Tasks on Hold:*\n"
            for member, tasks in blocked_tasks.items():
                message += f"• *{member}*:\n"
                for t in tasks:
                    deadline_str = f" (Deadline: {t['deadline']})" if t.get('deadline') else ""
                    description = t.get('description') or "Blocked task pending updates."
                    link = self._format_task_link(t.get('label'), t.get('id'), project_id)
                    message += f"    {link} {t['title']}{deadline_str} — {description}\n"
            message += "\n"

        message += "Please reply to this thread with your updates in the following format:\n"
        message += "1. What did you do yesterday?\n"
        message += "2. What are you planning to do today?\n"
        message += "3. Any blockers?\n\n"
        
        # Render tasks and suggestions by member
        all_members_set = set(grouped_tasks.keys()) | set(suggestions.keys() if suggestions else [])
        
        member_name_to_id = {}
        
        # Ensure all project members are included so we can show 'All tasks completed' for them
        from src.backend.model.project import Project, ProjectMember
        from src.backend.model.user import User
        project = self.db.query(Project).filter(Project.name == project_name).first()
        if project:
            members = self.db.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
            for m in members:
                u = self.db.query(User).get(m.user_id)
                if u and u.name:
                    all_members_set.add(u.name)
                    member_name_to_id[u.name] = str(u.id)
                    
        all_members = sorted(all_members_set)
        
        if all_members:
            message += "*Tasks by Member:*\n"
            for member in all_members:
                message += f"• *{member}:*\n"
                
                tasks = grouped_tasks.get(member, [])
                member_suggestions = suggestions.get(member, []) if suggestions else []
                
                inprogress_tasks = [t for t in tasks if t["status"] == "in_progress"]
                blocked_tasks = [t for t in tasks if t["status"] == "blocked"]
                
                has_shown_tasks = False
                
                if inprogress_tasks:
                    message += "  *⏳ In Progress:*\n"
                    for t in inprogress_tasks:
                        deadline_str = f" (Deadline: {t['deadline']})" if t.get('deadline') else ""
                        link = self._format_task_link(t.get('label'), t.get('id'), project_id)
                        message += f"    {link} {t['title']}{deadline_str}\n"
                    has_shown_tasks = True
                    
                if blocked_tasks:
                    message += "  *🚧 Blocked:*\n"
                    for t in blocked_tasks:
                        deadline_str = f" (Deadline: {t['deadline']})" if t.get('deadline') else ""
                        link = self._format_task_link(t.get('label'), t.get('id'), project_id)
                        message += f"    {link} {t['title']}{deadline_str}\n"
                    has_shown_tasks = True
                
                if not has_shown_tasks:
                    if member_suggestions:
                        message += "  💡 *Suggestions for today:* (Please reply with which one you'll take)\n"
                        for t in member_suggestions:
                            label = t.get('label')
                            link = self._format_task_link(label, t.get('id'), project_id)
                            deadline = t.get('deadline')
                            unassigned = " (Unassigned)" if t.get('is_unassigned') else ""
                            message += f"    - {link} {t['title']} [Deadline: {deadline}]{unassigned}\n"
                    else:
                        member_has_active_blocker = False
                        if active_blockers and active_blockers.get(member):
                            member_has_active_blocker = True
                                    
                        if member_has_active_blocker:
                            message += "  ⚠️ Waiting on active blockers.\n"
                        else:
                            message += "  ✅ All assigned tasks completed.\n"
                
                message += "\n"
        else:
            message += "There are currently no active tasks tracked in the system.\n"

        message += "\nLooking forward to hearing from everyone! 🚀"
        return message

    def _collect_current_blocked_tasks(self, grouped_tasks: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        blocked = {}
        for member, tasks in grouped_tasks.items():
            member_blocked = [t for t in tasks if t.get("status") == "blocked"]
            if member_blocked:
                blocked[member] = member_blocked
        return blocked


    def generate_standup_summary(self, project_id: str, project_name: str, updates: List[Dict[str, Any]], session_blockers: List[str], all_active_blockers: List[Dict[str, Any]] = None, insights: List[str] = None) -> str:
        """
        Generates a summary message of all processed updates.
        """
        message = f"✅ *Standup Summary for {project_name}*\n\n"
        
        if updates:
            # Filter out blocked status to avoid redundancy with the Blockers section
            filtered_updates = [up for up in updates if up.get("status", "").lower() != "blocked"]
            
            if filtered_updates:
                message += "*Updates:*\n"
                for up in filtered_updates:
                    user = up.get("user", "Someone")
                    task_raw = up.get("task") or "a task"
                    task = self._strip_to_self(task_raw) or "a task"
                    status = up.get("status", "").lower()
                    
                    if status == "completed":
                        message += f"• *{user}* has marked *{task}* as _completed_.\n"
                    elif status == "in_progress":
                        message += f"• *{user}* is now progressing on *{task}*.\n"
                    elif status == "todo":
                        message += f"• *{user}* has planned *{task}*.\n"
                    elif status == "resolved":
                        message += f"• *{user}* has _resolved_ the blocker: *{task.replace('blocker: ', '')}*.\n"
                    elif status == "newly created":
                        # Clean up phrasing like "Task Name to Rudraksh to Rudraksh" or "Task Name to self to Rudraksh"
                        clean_task = self._strip_to_self(task)
                        if f" to {user}" in clean_task:
                            clean_task = clean_task.split(f" to {user}")[0]
                        if " to self" in clean_task:
                            clean_task = clean_task.split(" to self")[0]
                        
                        message += f"• *{user}* introduced a new task: *{clean_task}*.\n"
                    elif status == "document_create":
                        message += f"• *{user}* created new document: *{task}*.\n"
                    elif status == "document_update":
                        message += f"• *{user}* updated document: *{task}*.\n"
                    else:
                        message += f"• *{user}* updated *{task}* to _{status}_\n"
            else:
                message += "No progress updates were recorded for this session"
                if session_blockers:
                    message += " (see new blockers below).\n"
                else:
                    message += ".\n"
        else:
            message += "No updates were recorded for this session.\n"

        # Consolidated Blocker Section
        if all_active_blockers:
            message += "\n🚧 *Current Project Blockers:*\n"
            
            # Categorize blockers
            task_blockers = [b for b in all_active_blockers if b.get("label")]
            general_blockers = [b for b in all_active_blockers if not b.get("label")]
            
            if task_blockers:
                message += "*Task-Related Blockers:*\n"
                for blk in task_blockers:
                    user = blk.get("user")
                    reason = blk.get("reason")
                    label = blk.get("label")
                    # Try to find task_id for this label
                    t_id = self.db.query(Task.id).filter(Task.project_id == project_id, Task.label == label).scalar()
                    link = self._format_task_link(label, str(t_id) if t_id else None, project_id)
                    message += f"• {link} (*{user}*): {reason}\n"
            
            if general_blockers:
                if task_blockers:
                    message += "\n"
                message += "*General Issues:*\n"
                for blk in general_blockers:
                    user = blk.get("user")
                    reason = blk.get("reason")
                    message += f"• (*{user}*): {reason}\n"

        if insights:
            message += "\n💡 *Strategy & Insights:*\n"
            for insight in insights:
                message += f"• {insight}\n"
        
        message += "\nGreat job team! Keep the momentum going. 📈"

        # Post-process message to turn any remaining [Task X] into Slack links
        final_message = ""
        for line in message.splitlines(keepends=True):
            clean_line = line
            # Find all [Task X] matches
            matches = re.finditer(r"\[Task (\d+)\]", clean_line)
            for m in matches:
                label_num = m.group(1)
                link = self._get_link_from_label(int(label_num), project_id)
                # Only replace the specific matched text
                clean_line = clean_line.replace(f"[Task {label_num}]", link)
            final_message += clean_line

        return final_message

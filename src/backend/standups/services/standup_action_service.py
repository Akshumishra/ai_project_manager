import uuid
import logging
import re
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.task import Task, TaskStatus, TaskPriority, TaskComplexity, TaskCategory
from src.backend.model.task_log import TaskLog
from src.backend.model.blocker import Blocker
from src.backend.model.project import ProjectMember
from src.backend.model.user import User
from src.backend.model.document import Document, DocumentBlock
from src.backend.standups.standup_agent.agent import StandupParsedResponse, NewTask
from src.backend.standups.services.standup_utils import StandupUtils

logger = logging.getLogger(__name__)

class StandupActionService:
    def __init__(self, db: Session):
        self.db = db

    async def apply_parsed_updates(self, update_id: uuid.UUID, parsed: StandupParsedResponse):
        """Applies the changes extracted by the AI Agent to the database."""
        try:
            standup_update = self.db.query(StandupUpdate).get(update_id)
            if not standup_update:
                logger.error(f"StandupUpdate {update_id} not found.")
                return

            # Log the parsed response for debugging
            logger.info(f"Applying parsed updates for {update_id}. Parsed: {parsed.model_dump_json()}")
            with open("/tmp/slack_events.log", "a") as f:
                f.write(f"[{datetime.now().ctime()}] Parsed Response: {parsed.model_dump_json()}\n")

            standup = self.db.query(Standup).get(standup_update.standup_id)
            member = self.db.query(ProjectMember).filter(
                ProjectMember.project_id == standup.project_id,
                ProjectMember.user_id == standup_update.user_id
            ).first()

            # Process updates
            for up in parsed.updates:
                await self._process_single_task_update(up, standup, member, update_id, parsed)

            # Handle blockers
            existing_active_blockers = self.db.query(Blocker).filter(
                Blocker.project_id == standup.project_id,
                Blocker.user_id == standup_update.user_id,
                Blocker.resolved_at.is_(None)
            ).all()
            
            if parsed.blockers:
                for blk in parsed.blockers:
                    await self._process_blocker(blk, standup, standup_update, existing_active_blockers, update_id)

            # Explicitly resolved blockers
            if hasattr(parsed, 'resolved_blockers') and parsed.resolved_blockers:
                await self._process_resolutions(parsed.resolved_blockers, standup, existing_active_blockers, update_id)

            # Handle sentiment
            if parsed.sentiment == "at_risk":
                await self._log_action(update_id, "SENTIMENT ALERT: Developer update indicates project risk.")

            # Handle documentation updates
            if parsed.doc_updates:
                for doc_up in parsed.doc_updates:
                    await self._process_doc_update(doc_up, standup, standup_update, update_id)

            # Handle new tasks
            if parsed.new_tasks:
                for new_t in parsed.new_tasks:
                    await self._process_new_task(new_t, standup, standup_update, update_id)
                    
        except Exception as e:
            logger.error(f"Failed to apply parsed updates for update {update_id}: {e}", exc_info=True)
            # We don't raise here to allow the caller (Manager) to handle it or continue
            raise e

    async def _process_single_task_update(self, up, standup, member, update_id, parsed):
        try:
            task = None
            if not up.task_id or up.task_id == "null":
                if hasattr(up, 'task_label') and up.task_label:
                    task = self.db.query(Task).filter(Task.project_id == standup.project_id, Task.label == up.task_label, Task.deleted_at.is_(None)).first()
                if not task:
                    task = StandupUtils.find_existing_task(self.db, standup.project_id, up.task_title, member.id if member else None)
                
                if not task:
                    new_t = NewTask(title=up.task_title, assignee=None, description=up.comment, deadline=up.deadline, complexity=up.complexity, status=up.new_status)
                    parsed.new_tasks.append(new_t)
                    return
            else:
                task = self.db.query(Task).get(up.task_id)

            if not task: return

            if member and task.project_member_id is None:
                task.project_member_id = member.id

            old_status = task.status.value.lower()
            new_status_obj = StandupUtils.safe_status_conversion(up.new_status)
            new_status_lower = new_status_obj.value
            
            if new_status_lower != old_status:
                task.status = new_status_obj
            
            if up.deadline:
                parsed_dt = StandupUtils.parse_deadline(up.deadline)
                if parsed_dt: task.deadline = parsed_dt
            if up.complexity:
                task.complexity = StandupUtils.safe_complexity_conversion(up.complexity)

            log_entry = f"Status: {new_status_lower}. Comment: {up.comment}" + (f" Deadline: {up.deadline}" if up.deadline else "") + (f" Complexity: {up.complexity}" if up.complexity else "") + " (via StandUp Agent)"
            self.db.add(TaskLog(task_id=task.id, log=log_entry))
            
            if new_status_lower in [TaskStatus.IN_PROGRESS.value, TaskStatus.COMPLETED.value]:
                await self._resolve_blockers_for_task(task, update_id, new_status_lower)

            label_str = f"[Task {task.label}] " if task.label else ""
            await self._log_action(update_id, f"Updated task {label_str}{task.title} status to {new_status_lower}")
        except Exception as e:
            logger.error(f"Error applying update for task {getattr(up, 'task_title', 'unknown')}: {e}")

    async def _process_blocker(self, blk, standup, standup_update, existing_active_blockers, update_id):
        try:
            # Skip if explicitly marked as RESOLVED (should be in resolved_blockers list instead)
            if hasattr(blk, 'type') and blk.type and str(blk.type).upper() == "RESOLVED":
                logger.info(f"Skipping blocker in 'blockers' list because type is RESOLVED for task {getattr(blk, 'task_label', 'general')}")
                return

            target_task_id = uuid.UUID(blk.task_id) if blk.task_id and blk.task_id != "null" else None
            if not target_task_id and hasattr(blk, 'task_label') and blk.task_label:
                t = self.db.query(Task).filter(Task.project_id == standup.project_id, Task.label == blk.task_label, Task.deleted_at.is_(None)).first()
                if t: target_task_id = t.id

            # Enhanced matching using task_id, task_label, or task_title
            matched_blocker = None
            ignore_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by", "with", "from", "blocked", "resolved", "fixed", "no", "longer", "issue"}
            
            # 1. Try matching by task_id
            if target_task_id:
                matched_blocker = next((eb for eb in existing_active_blockers if eb.task_id == target_task_id), None)
            
            # 2. Try matching by task_label or reason overlap
            if not matched_blocker:
                for eb in existing_active_blockers:
                    # Match by task_label if both have it
                    if hasattr(blk, 'task_label') and blk.task_label and eb.task and eb.task.label == blk.task_label:
                        matched_blocker = eb
                        break
                    
                    # Fuzzy match by reason overlap
                    eb_words = set(re.findall(r'\w+', eb.reason.lower())) - ignore_words
                    blk_words = set(re.findall(r'\w+', blk.reason.lower())) - ignore_words
                    if eb_words and blk_words and len(eb_words.intersection(blk_words)) >= min(len(eb_words), len(blk_words), 3):
                        matched_blocker = eb
                        break
            
            if matched_blocker:
                matched_blocker.reason = blk.reason
                matched_blocker.blocked_by = blk.blocked_by
                matched_blocker.impact = blk.impact
            else:
                new_blocker = Blocker(project_id=standup.project_id, user_id=standup_update.user_id, task_id=target_task_id, reason=blk.reason, blocked_by=blk.blocked_by, impact=blk.impact)
                self.db.add(new_blocker)
                if target_task_id:
                    task = self.db.query(Task).get(target_task_id)
                    if task: task.status = TaskStatus.BLOCKED

            label_or_title = ""
            if hasattr(blk, 'task_label') and blk.task_label:
                label_or_title = f" in [Task {blk.task_label}]"
            elif hasattr(blk, 'task_title') and blk.task_title and blk.task_title != "General":
                label_or_title = f" in task '{blk.task_title}'"

            log_msg = f"BLOCKER ({blk.type}): Blocked" + (f" by {blk.blocked_by}" if blk.blocked_by else "") + f"{label_or_title} due to: {blk.reason}. Impact: {blk.impact}."
            await self._log_action(update_id, log_msg)
        except Exception as e:
            logger.error(f"Error applying blocker update: {e}")

    async def _process_resolutions(self, resolutions, standup, existing_active_blockers, update_id):
        ignore_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by", "with", "from", "blocked", "resolved", "fixed", "no", "longer", "issue", "waiting", "proceed", "work"}
        for res in resolutions:
            matched = None
            if res.task_label:
                matched = self.db.query(Blocker).join(Task).filter(Blocker.project_id == standup.project_id, Task.label == res.task_label, Blocker.resolved_at.is_(None)).first()
            if not matched and res.reason:
                res_words = set(re.findall(r'\w+', res.reason.lower())) - ignore_words
                if res_words:
                    best, high = None, 0
                    for eb in existing_active_blockers:
                        inter = len((set(re.findall(r'\w+', eb.reason.lower())) - ignore_words).intersection(res_words))
                        if inter > high: best, high = eb, inter
                    matched = best
                if not matched and len(existing_active_blockers) == 1: matched = existing_active_blockers[0]

            if matched:
                matched.resolved_at = datetime.now(timezone.utc)
                await self._log_action(update_id, f"RESOLVED BLOCKER: {matched.reason}")
                if matched.task_id:
                    task = self.db.query(Task).get(matched.task_id)
                    if task and task.status == TaskStatus.BLOCKED:
                        task.status = TaskStatus.IN_PROGRESS

    async def _process_doc_update(self, doc_up, standup, standup_update, update_id):
        try:
            doc = self.db.query(Document).filter(Document.project_id == standup.project_id, Document.title.ilike(doc_up.title), Document.deleted_at.is_(None)).first()
            is_new = False
            if not doc:
                deleted = self.db.query(Document).filter(Document.project_id == standup.project_id, Document.title.ilike(doc_up.title), Document.deleted_at.isnot(None)).first()
                if deleted: doc, doc.deleted_at, is_new = deleted, None, True
                else: doc, is_new = Document(project_id=standup.project_id, title=doc_up.title, created_by=standup_update.user_id), True
                self.db.add(doc)
                self.db.flush()

            last = self.db.query(DocumentBlock).filter(DocumentBlock.doc_id == doc.id).order_by(DocumentBlock.position_key.desc()).first()
            next_pos = str(int(last.position_key) + 1).zfill(3) if last else "001"
            self.db.add(DocumentBlock(doc_id=doc.id, content=doc_up.content, position_key=next_pos, type="paragraph", last_edited_by=standup_update.user_id))
            await self._log_action(update_id, f"{'CREATED NEW DOCUMENT' if is_new else 'UPDATED DOCUMENT'}: {doc_up.title} with new info.")
        except Exception as e:
            logger.error(f"Error applying doc update {doc_up.title}: {e}")

    async def _process_new_task(self, new_t, standup, standup_update, update_id):
        try:
            target_id = None
            if new_t.assignee:
                member = self.db.query(ProjectMember).join(User).filter(ProjectMember.project_id == standup.project_id, User.name.ilike(new_t.assignee)).first()
                if member: target_id = member.id
            if not target_id:
                member = self.db.query(ProjectMember).filter(ProjectMember.project_id == standup.project_id, ProjectMember.user_id == standup_update.user_id).first()
                if member: target_id = member.id
            
            if target_id:
                parsed_dt = StandupUtils.parse_deadline(new_t.deadline)
                default_dt = datetime.now(timezone.utc) + timedelta(days=7) if not parsed_dt else None
                status = StandupUtils.safe_status_conversion(new_t.status)
                
                existing = StandupUtils.find_existing_task(self.db, standup.project_id, new_t.title, target_id)
                if existing:
                    existing.status = status
                    if parsed_dt: existing.deadline = parsed_dt
                    elif default_dt and existing.deadline is None: existing.deadline = default_dt
                    task_obj = existing
                else:
                    task_obj = Task(
                        title=new_t.title, 
                        project_id=standup.project_id, 
                        description=new_t.description or f"Created via StandUp Agent", 
                        status=status, 
                        project_member_id=target_id, 
                        deadline=parsed_dt or default_dt, 
                        complexity=StandupUtils.safe_complexity_conversion(new_t.complexity),
                        priority=TaskPriority.MEDIUM, # Default
                        category=TaskCategory.BACKEND # Mandatory default
                    )
                    if new_t.deadline and not parsed_dt: task_obj.description += f" (Deadline: {new_t.deadline})"
                    self.db.add(task_obj)
                self.db.flush()
                
                self.db.add(TaskLog(task_id=task_obj.id, log=f"Task created via Agent. {new_t.deadline or 'default deadline'}"))
                label_str = f"[Task {task_obj.label}] " if task_obj.label else ""
                await self._log_action(update_id, f"CREATED NEW TASK: {label_str}{new_t.title}{' to ' + new_t.assignee if new_t.assignee else ''}")
        except Exception as e:
            logger.error(f"Error applying new task creation: {e}")

    async def _resolve_blockers_for_task(self, task, update_id, new_status):
        active = self.db.query(Blocker).filter(Blocker.task_id == task.id, Blocker.resolved_at.is_(None)).all()
        for b in active:
            b.resolved_at = datetime.now(timezone.utc)
            await self._log_action(update_id, f"Resolved blocker: {b.reason} (Auto-resolved because task '{task.title}' moved to {new_status})")

    async def _log_action(self, update_id, text):
        if not self.db.query(StandupActionLog).filter(StandupActionLog.update_id == update_id, StandupActionLog.action_taken == text).first():
            self.db.add(StandupActionLog(update_id=update_id, action_taken=text))
            self.db.flush()

import logging
import uuid
import re
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from src.backend.config import settings
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.task import Task, TaskStatus
from src.backend.model.task_log import TaskLog
from src.backend.model.project import ProjectMember, Project, ProjectSlackDetail
from src.backend.model.user import User
from src.backend.slack.services.slack_service import SlackService
from src.backend.standups.services.standup_generator import StandupGenerator
from src.backend.standups.standup_agent.agent import StandupReplyAgent
from src.backend.standups.services.standup_utils import StandupUtils
from src.backend.standups.services.standup_repository import StandupRepository
from src.backend.standups.services.standup_action_service import StandupActionService

logger = logging.getLogger(__name__)

class StandupManager:
    def __init__(self, db: Session):
        self.db = db
        self.slack_service = SlackService()
        self.generator = StandupGenerator(db)
        self.agent = StandupReplyAgent()
        # Specialized services
        self.repo = StandupRepository(db, self.agent, self.generator)
        self.action_service = StandupActionService(db)

    async def initiate_all_standups(self) -> Dict[str, str]:
        """Initiates standups for all projects with Slack configured."""
        results = {}
        details = self.db.query(ProjectSlackDetail).all()
        for detail in details:
            if detail.channel_id:
                ts = await self.initiate_standup(str(detail.project_id), detail.channel_id)
                if ts: results[str(detail.project_id)] = ts
        return results

    async def initiate_standup(self, project_id: str, channel_id: str) -> Optional[str]:
        """Starts a new standup session by posting to Slack."""
        try:
            # Data gathering delegated to Repo/Generator
            try:
                grouped_tasks, overdue_tasks, suggestions = await self.generator.fetch_active_tasks(project_id)
                active_blockers = await self.generator.fetch_active_blockers(project_id)
                historical_highlights, summary_insights = await self.repo.get_historical_highlights(project_id)
                missed_members = await self.repo.get_missed_update_members(project_id, grouped_tasks)
            except Exception as e:
                logger.error(f"Data gathering failed for project {project_id}: {e}")
                raise ValueError(f"Could not gather project data: {e}")

            project = self.db.query(Project).get(project_id)
            project_name = project.name if project else "Project"
            
            # Prompt generation
            try:
                raw = await self.generator.generate_standup_prompt(str(project_id), project_name, grouped_tasks, overdue_tasks, suggestions, historical_highlights, active_blockers, missed_members, summary_insights)
                prompt_text = await self.agent.refine_standup_prompt(project_name, raw)
            except Exception as e:
                logger.error(f"Agent prompt refinement failed for {project_name}: {e}")
                prompt_text = raw # Fallback to raw if agent fails

            # Execution
            try:
                ts = self.slack_service.post_message(channel_id, prompt_text)
                if not ts:
                    raise Exception("Slack service returned empty timestamp")
            except Exception as e:
                logger.error(f"Slack post failed for {channel_id}: {e}")
                raise ConnectionError(f"Slack integration error: {e}")

            self.db.add(Standup(project_id=uuid.UUID(str(project_id)), slack_channel_id=channel_id, message_ts=ts, prompt=prompt_text))
            self.db.commit()
            return ts
        except Exception as e:
            logger.error(f"Failed to initiate standup for project {project_id}: {e}", exc_info=True)
            self.db.rollback()
            raise e # Propagate to route

    async def process_new_replies(self, standup_id: str):
        """Processes new replies from the Slack thread via AI and ActionService (Backup/Scheduler)."""
        try:
            standup_uuid = uuid.UUID(standup_id) if isinstance(standup_id, str) else standup_id
            standup = self.db.query(Standup).get(standup_uuid)
            if not standup: 
                logger.warning(f"Standup {standup_id} not found for reply processing.")
                return

            try:
                replies = self.slack_service.list_replies(standup.slack_channel_id, standup.message_ts)
            except Exception as e:
                logger.error(f"Failed to fetch Slack replies for standup {standup_id}: {e}")
                return
            
            for reply in replies[1:]:
                user_slack_id = reply.get("user")
                raw_text = reply.get("text", "")
                reply_ts = reply.get("ts")

                # Resolve mentions and clean text
                text = self._prepare_reply_text(raw_text, standup.project_id)
                if self._is_already_processed(standup.id, reply_ts, text): continue

                # Identify member
                member = self.db.query(ProjectMember).filter(ProjectMember.project_id == standup.project_id, ProjectMember.slack_id == user_slack_id).first()
                if not member or (settings.BOT_USER_ID and user_slack_id == settings.BOT_USER_ID):
                    continue

                try:
                    await self._process_and_save_reply(member, standup, text, reply_ts)
                except Exception as e:
                    logger.error(f"Error processing specific direct reply from {user_slack_id}: {e}")
        except Exception as e:
            logger.error(f"Critical error in process_new_replies for standup {standup_id}: {e}")
            raise e

    async def handle_reply_event(self, standup_id: str, user_slack_id: str, text: str, reply_ts: str):
        """Processes a single Slack reply event in real-time."""
        try:
            standup_uuid = uuid.UUID(standup_id) if isinstance(standup_id, str) else standup_id
            standup = self.db.query(Standup).get(standup_uuid)
            if not standup: return

            # Resolve mentions and clean text
            clean_text = self._prepare_reply_text(text, standup.project_id)
            if self._is_already_processed(standup.id, reply_ts, clean_text): 
                logger.info(f"Reply {reply_ts} already processed.")
                return

            # Identify member
            member = self.db.query(ProjectMember).filter(ProjectMember.project_id == standup.project_id, ProjectMember.slack_id == user_slack_id).first()
            if not member or (settings.BOT_USER_ID and user_slack_id == settings.BOT_USER_ID): 
                logger.info(f"User {user_slack_id} is not a project member or is the bot.")
                return

            await self._process_and_save_reply(member, standup, clean_text, reply_ts)
        except Exception as e:
            logger.error(f"Error in handle_reply_event for standup {standup_id}: {e}")

    async def _process_and_save_reply(self, member, standup, text, reply_ts):
        """Internal helper to process a reply through AI and save to DB."""
        try:
            logger.info(f"Step 1: Saving raw update for member {member.user_id}")
            # 1. Persistence - Save RAW update first
            update = StandupUpdate(standup_id=standup.id, user_id=member.user_id, reply_text=text, slack_ts=reply_ts)
            self.db.add(update)
            self.db.flush()
            logger.info(f"Step 1 COMPLETE: Saved update ID {update.id}")
            
            # 2. Context gathering & Agent Context
            logger.info("Step 2: Gathering context and active tasks")
            active_tasks, _, suggestions = await self.generator.fetch_active_tasks(str(standup.project_id))
            user = self.db.query(User).get(member.user_id)
            user_name = user.name if user else "Developer"
            
            agent_context = await self._prepare_agent_context(text, member, standup, active_tasks, suggestions, user_name)
            logger.info("Step 2 COMPLETE: Agent context prepared")
            
            # 3. Call Agent
            logger.info("Step 3: Calling AI Agent and applying updates")
            try:
                # Remove non-agent arguments from context
                agent_args = {k: v for k, v in agent_context.items() if k != "selected_task"}
                parsed = await self.agent.parse_reply(**agent_args)
                logger.info(f"Agent parsed reply. Extracted {len(parsed.updates)} updates, {len(parsed.blockers)} blockers")
                
                # Apply Actions from parsed result
                if agent_context.get("selected_task"):
                    logger.info(f"Logging task selection for task {agent_context['selected_task'].id}")
                    StandupUtils.log_task_selection_action(self.db, update.id, agent_context["selected_task"])
                
                await self.action_service.apply_parsed_updates(update.id, parsed)
                logger.info("Action application complete")
                
            except Exception as e:
                logger.error(f"Agent parse or action application error for member {user_name} in standup {standup.id}: {e}", exc_info=True)
                # We still keep the update saved, just without the parsed actions
            
            logger.info("Final Step: Committing transaction")
            self.db.commit()
            logger.info(f"Successfully processed and saved standup update for {user_name}")
        except Exception as e:
            self.db.rollback()
            raise e

    async def finalize_all_active_standups(self):
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        standups = self.db.query(Standup).filter(Standup.created_at >= cutoff, Standup.summary.is_(None), Standup.deleted_at.is_(None)).all()
        processed_ids = []
        for standup in standups:
            try:
                await self.process_new_replies(str(standup.id))
                await self.finalize_standup(str(standup.id))
                processed_ids.append(str(standup.id))
            except Exception as e:
                logger.error(f"Failed to auto-finalize {standup.id}: {e}")
        return processed_ids

    async def finalize_standup(self, standup_id: str):
        """Generates evening summary and posts to Slack."""
        try:
            standup_uuid = uuid.UUID(standup_id) if isinstance(standup_id, str) else standup_id
            standup = self.db.query(Standup).get(standup_uuid)
            if not standup: return

            updates = self.db.query(StandupUpdate).filter(StandupUpdate.standup_id == standup.id, StandupUpdate.deleted_at.is_(None)).all()
            if not updates:
                logger.info(f"No updates for standup {standup_id}. Skipping summary.")
                summary_text = "No updates provided for this session."
                try:
                    self.slack_service.post_message(standup.slack_channel_id, f"📝 *Standup Summary*: {summary_text}", thread_ts=standup.message_ts)
                except Exception as e:
                    logger.error(f"Failed to post empty summary to Slack for {standup_id}: {e}")
                
                standup.summary = summary_text
                self.db.commit()
                return

            summary_updates, session_blockers, session_insights = [], [], []
            seen = set()

            for up in updates:
                user_name = (self.db.query(User.name).filter(User.id == up.user_id).scalar()) or "Unknown"
                for log in self.db.query(StandupActionLog).filter(StandupActionLog.update_id == up.id).all():
                    self._parse_action_for_summary(log.action_taken, user_name, summary_updates, session_blockers, session_insights, seen)

            # Post summary
            try:
                summary_text = await self.generator.generate_standup_summary(str(standup.project_id), "Project", summary_updates, session_blockers, None, session_insights)
                self.slack_service.post_message(standup.slack_channel_id, summary_text, thread_ts=standup.message_ts)
            except Exception as e:
                logger.error(f"Slack summary post failed for standup {standup_id}: {e}")
                raise ConnectionError(f"Could not post summary to Slack: {e}")

            standup.summary = summary_text
            self.db.commit()
        except Exception as e:
            logger.error(f"Error finalizing standup {standup_id}: {e}")
            self.db.rollback()
            raise e

    # Private Orchestration Helpers
    def _prepare_reply_text(self, raw_text: str, project_id: uuid.UUID) -> str:
        mentions = re.findall(r'<@(U[A-Z0-9]+)>', raw_text)
        text = raw_text
        for m_id in mentions:
            member = self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.slack_id == m_id).first()
            if member:
                u = self.db.query(User).get(member.user_id)
                if u: text = text.replace(f"<@{m_id}>", u.name)
        return re.sub(r'[*_]{1,2}', '', text).strip()

    def _is_already_processed(self, standup_id, reply_ts, text) -> bool:
        return self.db.query(StandupUpdate).filter(StandupUpdate.standup_id == standup_id, StandupUpdate.deleted_at.is_(None)).filter((StandupUpdate.slack_ts == reply_ts) | (StandupUpdate.reply_text == text)).first() is not None

    async def _prepare_agent_context(self, text, member, standup, active_tasks, suggestions, user_name):
        user_tasks = active_tasks.get(user_name, [])
        user_suggestions = suggestions.get(user_name, [])
        unassigned = [s for s_list in suggestions.values() for s in s_list if s.get("is_unassigned") and s["id"] not in {t["id"] for t in user_suggestions}]
        
        # Intelligent Blocker retrieval logic (could be moved to repo if needed)
        past_summaries = "\n".join([f"Date: {s.created_at}, Summary: {s.summary}" for s in self.db.query(Standup).filter(Standup.project_id == standup.project_id, Standup.summary.isnot(None)).order_by(Standup.created_at.desc()).limit(10).all()])
        past_todos = "\n".join([f"ID: {t.id}, Title: {t.title}" for t in self.db.query(Task).filter(Task.project_id == standup.project_id, Task.status == TaskStatus.TODO).all()])
        
        intelligent_blk = await self.agent.identify_blocker(standup_message=text, members_with_active_tasks=json.dumps(active_tasks), standup_summaries=past_summaries, todo_tasks=past_todos)
        
        selected_task = StandupUtils.detect_task_selection(self.db, text, member, standup.project_id)

        return {
            "user_name": user_name,
            "reply_text": text,
            "active_tasks": user_tasks + user_suggestions + unassigned,
            "has_in_progress_tasks": any(t.get("status") == "in_progress" for t in user_tasks),
            "team_members": [u.name for u in self.db.query(User).join(ProjectMember).filter(ProjectMember.project_id == standup.project_id).all()],
            "message_date": datetime.now(timezone.utc), # simplified
            "selected_task": selected_task
        }

    def _parse_action_for_summary(self, action, user, summary, blockers, insights, seen):
        if "Updated task" in action:
            p = action.split("Updated task ")[1].split(" status to ")
            if (user, p[0], p[1]) not in seen:
                summary.append({"user": user, "task": p[0], "status": p[1]})
                seen.add((user, p[0], p[1]))
        elif "BLOCKER (" in action:
            blockers.append(f"{user}: {action.split(': ', 1)[1]}")
        elif "RESOLVED BLOCKER: " in action:
            msg = action.split("RESOLVED BLOCKER: ")[1]
            if (user, f"blocker: {msg}", "resolved") not in seen:
                summary.append({"user": user, "task": f"blocker: {msg}", "status": "resolved"})
                seen.add((user, f"blocker: {msg}", "resolved"))
        elif "SENTIMENT ALERT: " in action:
            insights.append(f"Risk Warning: {user}'s update suggests project risk.")
        elif any(px in action for px in ["CREATED NEW TASK", "TODO: ", "IN_PROGRESS: ", "COMPLETED: ", "BLOCKED: "]):
            if "CREATED NEW TASK" in action:
                task = action.split("CREATED NEW TASK: ")[1]
                summary.append({"user": user, "task": task, "status": "newly created"})

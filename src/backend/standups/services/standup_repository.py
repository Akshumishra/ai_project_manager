import uuid
import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.project import ProjectMember
from src.backend.model.user import User
from src.backend.standups.services.standup_utils import StandupUtils

logger = logging.getLogger(__name__)

class StandupRepository:
    def __init__(self, db: Session, agent=None, generator=None):
        self.db = db
        self.agent = agent
        self.generator = generator

    async def get_historical_highlights(self, project_id: str) -> tuple[Dict[str, Dict[str, Any]], List[str]]:
        """Retrieves highlights from the last completed standup session."""
        standups = (
            self.db.query(Standup)
            .filter(Standup.project_id == uuid.UUID(str(project_id)))
            .order_by(Standup.created_at.desc())
            .all()
        )

        fallback = {}
        selected_highlights = None

        for standup in standups:
            if not standup.updates:
                continue

            highlights = await self.build_standup_highlights(standup)
            if not highlights:
                continue

            if not fallback:
                fallback = highlights

            if await self.highlights_have_blockers(highlights):
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
        summary_insights = await self.extract_summary_insights(
            latest_summary_standup.summary if latest_summary_standup else None
        )

        return selected_highlights, summary_insights

    async def build_standup_highlights(self, standup: Standup) -> Dict[str, Dict[str, Any]]:
        highlights = {}
        for update in standup.updates:
            user_name = update.user.name if update.user else "Unknown"
            if user_name not in highlights:
                highlights[user_name] = {"raw_texts": [], "action_lists": [], "blockers": [], "new_tasks": []}

            for log in update.action_logs:
                if "BLOCKER" in log.action_taken:
                    highlights[user_name]["blockers"].append(StandupUtils.parse_blocker_action(log.action_taken))
                new_task_name = StandupUtils.extract_new_task_name(log.action_taken, user_name)
                if new_task_name:
                    highlights[user_name]["new_tasks"].append(new_task_name)

            highlights[user_name]["raw_texts"].append(update.reply_text)
            highlights[user_name]["action_lists"].extend([log.action_taken for log in update.action_logs])

        for user_name, data in highlights.items():
            combined_text = "\n".join(data["raw_texts"])
            summary = await self.agent.summarize_update(user_name, combined_text, data["action_lists"]) if self.agent else combined_text
            highlights[user_name] = {"summary": summary, "blockers": data["blockers"], "new_tasks": data["new_tasks"]}

        if not await self.project_has_active_blocked_tasks(str(standup.project_id)):
            for data in highlights.values():
                data["blockers"] = []
        return highlights

    async def highlights_have_blockers(self, highlights: Dict[str, Dict[str, Any]]) -> bool:
        return any(hl.get("blockers") for hl in highlights.values())

    async def extract_summary_insights(self, summary_text: Optional[str]) -> List[str]:
        if not summary_text:
            return []
        lines = [line.strip() for line in summary_text.splitlines()]
        insights = []
        for line in lines:
            if not line or not line.startswith("•"):
                continue
            insight = line.lstrip("•").strip()
            insight = re.sub(r"\s+to\s+self\b", "", insight, flags=re.IGNORECASE)
            insight = re.sub(r"\s{2,}", " ", insight).strip()
            if insight and insight != "Great job team! Keep the momentum going. :chart_with_upwards_trend:":
                insights.append(insight)
        return insights

    async def project_has_active_blocked_tasks(self, project_id: str) -> bool:
        if not self.generator: return False
        grouped_tasks, _, _ = await self.generator.fetch_active_tasks(project_id)
        return any(task.get("status") == "blocked" for tasks in grouped_tasks.values() for task in tasks)

    async def get_missed_update_members(self, project_id: str, grouped_tasks: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        last_standup = (
            self.db.query(Standup)
            .filter(Standup.project_id == uuid.UUID(str(project_id)))
            .order_by(Standup.created_at.desc())
            .first()
        )
        if not last_standup: return []
        update_user_ids = {u.user_id for u in last_standup.updates}
        missed_members = []
        for member_name in grouped_tasks.keys():
            member = self.db.query(ProjectMember).join(User).filter(
                ProjectMember.project_id == uuid.UUID(str(project_id)),
                User.name == member_name
            ).first()
            if member and member.user_id not in update_user_ids:
                missed_members.append(member_name)
        return missed_members

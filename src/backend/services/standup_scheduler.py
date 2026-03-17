import logging
import time
from typing import List
from src.backend.services.standup_manager import StandupManager
from src.backend.db.database_standup import SessionStandup
from src.backend.model.project import Project, ProjectSlackDetail

logger = logging.getLogger(__name__)

class StandupScheduler:
    """
    Handles triggering standups for all active projects.
    In a real system, this would be tied to a cron job or APScheduler.
    """
    def __init__(self):
        self.db = SessionStandup()
        self.manager = StandupManager(self.db)

    def trigger_all_active_standups(self):
        """
        Finds all active projects with Slack details and starts a standup.
        """
        try:
            active_projects = (
                self.db.query(Project)
                .join(ProjectSlackDetail)
                .filter(Project.status == "active")
                .all()
            )

            for project in active_projects:
                slack_detail = project.slack_details[0] if project.slack_details else None
                if slack_detail and slack_detail.channel_id:
                    logger.info(f"Triggering standup for {project.name}")
                    self.manager.initiate_standup(str(project.id), slack_detail.channel_id)
            
        except Exception as e:
            logger.error(f"Error in standup scheduler: {e}")
        finally:
            self.db.close()

def run_worker():
    """Simple worker entry point."""
    scheduler = StandupScheduler()
    logger.info("Standup worker started.")
    scheduler.trigger_all_active_standups()

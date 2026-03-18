import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.backend.db.database_standup import SessionStandup
from src.backend.services.standup_manager import StandupManager

logger = logging.getLogger(__name__)

class StandupScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    def _get_manager(self):
        # We create a new session/manager per job run to avoid stale connections
        db = SessionStandup()
        return StandupManager(db), db

    async def morning_job(self):
        logger.info("CRON: Starting morning standup initiation...")
        manager, db = self._get_manager()
        try:
            results = manager.initiate_all_standups()
            logger.info(f"CRON: Morning standups initiated for {len(results)} projects.")
        except Exception as e:
            logger.error(f"CRON: Error in morning job: {e}")
        finally:
            db.close()

    async def evening_job(self):
        logger.info("CRON: Starting evening standup finalization...")
        manager, db = self._get_manager()
        try:
            results = manager.finalize_all_active_standups()
            logger.info(f"CRON: Evening standups finalized: {results}")
        except Exception as e:
            logger.error(f"CRON: Error in evening job: {e}")
        finally:
            db.close()

    def start(self):
        # Morning standup at 9:30 AM Mon-Fri
        self.scheduler.add_job(
            self.morning_job,
            CronTrigger(day_of_week='mon-fri', hour=9, minute=42),
            id='morning_standup',
            replace_existing=True
        )
        
        # Evening finalization at 6:00 PM Mon-Fri
        self.scheduler.add_job(
            self.evening_job,
            CronTrigger(day_of_week='mon-fri', hour=18, minute=0),
            id='evening_standup',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Standup Scheduler started (9:30 AM & 6:00 PM).")

    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("Standup Scheduler shut down.")

# Singleton instance
standup_scheduler = StandupScheduler()

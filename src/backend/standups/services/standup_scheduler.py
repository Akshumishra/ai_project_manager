import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.backend.db.database_standup import SessionStandup
from src.backend.standups.services.standup_manager import StandupManager

logger = logging.getLogger(__name__)

class StandupScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    def _get_manager(self):
        db = SessionStandup()
        return StandupManager(db), db

    def morning_job(self):
        logger.info("CRON: Starting morning standup initiation...")
        manager, db = self._get_manager()
        try:
            results = manager.initiate_all_standups()
            logger.info(f"CRON: Morning standups initiated for {len(results)} projects.")
        except Exception as e:
            logger.error(f"CRON: Error in morning job: {e}")
        finally:
            db.close()

    def evening_job(self):
        logger.info("CRON: Starting evening standup finalization...")
        manager, db = self._get_manager()
        try:
            results = manager.finalize_all_active_standups()
            logger.info(f"CRON: Evening standups finalized: {results}")
        except Exception as e:
            logger.error(f"CRON: Error in evening job: {e}")
        finally:
            db.close()

    def startup_finalize_job(self):
        """
        Runs once on startup. Finalizes any standups that were created today but
        not yet summarized — handles cases where the evening cron was missed.
        """
        logger.info("STARTUP: Checking for any unfinalized standups...")
        manager, db = self._get_manager()
        try:
            results = manager.finalize_all_active_standups()
            if results:
                logger.info(f"STARTUP: Finalized {len(results)} pending standup(s): {results}")
            else:
                logger.info("STARTUP: No unfinalized standups found.")
        except Exception as e:
            logger.error(f"STARTUP: Error during startup finalization: {e}")
        finally:
            db.close()

    def start(self):
        # Morning standup Mon-Fri IST
        # misfire_grace_time=3600 → fires even if server starts up to 1 hour late
        self.scheduler.add_job(
            self.morning_job,
            CronTrigger(day_of_week='mon-fri', hour=13, minute=45, timezone='Asia/Kolkata'),
            id='morning_standup',
            replace_existing=True,
            misfire_grace_time=3600
        )
        
        # Evening finalization Mon-Fri IST
        self.scheduler.add_job(
            self.evening_job,
            CronTrigger(day_of_week='mon-fri', hour=13, minute=53, timezone='Asia/Kolkata'),
            id='evening_standup',
            replace_existing=True,
            misfire_grace_time=3600
        )

        # One-shot startup job: runs 5 seconds after server starts.
        # Finalizes any standups pending from today that the cron may have missed.
        from apscheduler.triggers.date import DateTrigger
        from datetime import datetime, timezone, timedelta
        run_at = datetime.now(timezone.utc) + timedelta(seconds=5)
        self.scheduler.add_job(
            self.startup_finalize_job,
            DateTrigger(run_date=run_at),
            id='startup_finalize',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Standup Scheduler started. Startup finalization will run in 5 seconds.")

    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("Standup Scheduler shut down.")

# Singleton instance
standup_scheduler = StandupScheduler()

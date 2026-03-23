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

    async def initiate_daily_standups(self):
        logger.info("CRON: Starting morning standup initiation...")
        manager, db = self._get_manager()
        try:
            results = await manager.initiate_all_standups()
            logger.info(f"CRON: Morning standups initiated for {len(results)} projects.")
        except Exception as e:
            logger.error(f"CRON: Error in initiate_daily_standups: {e}")
        finally:
            db.close()

    async def finalize_daily_standups(self):
        logger.info("CRON: Starting evening standup finalization...")
        manager, db = self._get_manager()
        try:
            results = await manager.finalize_all_active_standups()
            logger.info(f"CRON: Evening standups finalized: {results}")
        except Exception as e:
            logger.error(f"CRON: Error in finalize_daily_standups: {e}")
        finally:
            db.close()

    async def run_startup_finalization_check(self):
        """
        Runs once on startup. Finalizes any standups that were created today but
        not yet summarized — handles cases where the evening cron was missed.
        """
        logger.info("STARTUP: Checking for any unfinalized standups...")
        manager, db = self._get_manager()
        try:
            results = await manager.finalize_all_active_standups()
            if results:
                logger.info(f"STARTUP: Finalized {len(results)} pending standup(s): {results}")
            else:
                logger.info("STARTUP: No unfinalized standups found.")
        except Exception as e:
            logger.error(f"STARTUP: Error during startup finalization: {e}")
        finally:
            db.close()

    def start(self):
        # Morning standup Mon-Fri IST (9:30 AM)
        self.scheduler.add_job(
            self.initiate_daily_standups,
            CronTrigger(day_of_week='mon-fri', hour=9, minute=30, timezone='Asia/Kolkata'),
            id='morning_standup',
            replace_existing=True,
            misfire_grace_time=3600
        )
        
        # Evening finalization Mon-Fri IST (6:30 PM)
        self.scheduler.add_job(
            self.finalize_daily_standups,
            CronTrigger(day_of_week='mon-fri', hour=18, minute=30, timezone='Asia/Kolkata'),
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
            self.run_startup_finalization_check,
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


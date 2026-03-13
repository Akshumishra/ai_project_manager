from apscheduler.schedulers.background import BackgroundScheduler
from .block_sync_worker import flush_dirty_blocks

scheduler = BackgroundScheduler()

scheduler.add_job(flush_dirty_blocks, "interval", minutes=1)


def start_scheduler():
    scheduler.start()

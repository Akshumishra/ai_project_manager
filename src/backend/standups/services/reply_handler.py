from __future__ import annotations
import logging
from src.backend.db.database_standup import SessionStandup
from src.backend.model.standup import Standup
from src.backend.standups.services.standup_manager import StandupManager

logger = logging.getLogger(__name__)

async def handle_standup_reply(
    channel_id: str,
    thread_ts: str,
    slack_user_id: str,
    user_text: str,
    ts: str
):
    """
    Handles a thread reply that is suspected to be a standup update.
    """
    logger.info(f"Handling standup reply: channel={channel_id}, thread_ts={thread_ts}, user={slack_user_id}")
    db = SessionStandup()
    try:
        # 1. Try exact match
        standup = db.query(Standup).filter(
            Standup.message_ts == thread_ts,
            Standup.slack_channel_id == channel_id
        ).first()
        
        if standup:
            logger.info(f"Match found: Exact match with standup {standup.id}")
        
        # 2. Try nearby match (sometimes Slack TS differs slightly)
        if not standup:
            logger.info(f"No exact match for thread_ts {thread_ts}. Attempting fuzzy match...")
            try:
                ts_float = float(thread_ts)
                all_standups = db.query(Standup).filter(
                    Standup.slack_channel_id == channel_id
                ).order_by(Standup.created_at.desc()).limit(5).all()
                
                logger.debug(f"Checking {len(all_standups)} recent standups in channel {channel_id}")
                for s in all_standups:
                    try:
                        s_ts = float(s.message_ts)
                        diff = abs(ts_float - s_ts)
                        logger.debug(f"Comparing thread_ts {ts_float} with s.message_ts {s_ts} (diff: {diff})")
                        if diff < 1.0: # 1 second window
                            standup = s
                            logger.info(f"Match found: Fuzzy match with standup {standup.id} (diff: {diff})")
                            break
                    except:
                        continue
            except Exception as e:
                logger.error(f"Epsilon match failed: {e}")

        if standup:
            logger.info(f"FOUND standup {standup.id}. Processing reply from {slack_user_id}")
            manager = StandupManager(db)
            await manager.handle_reply_event(str(standup.id), slack_user_id, user_text, ts)
            return True
        else:
            logger.warning(f"Thread {thread_ts} in channel {channel_id} is NOT a known standup. Ignoring.")
            return False
    except Exception as e:
        logger.error(f"Standup reply processing failed for thread {thread_ts}: {e}", exc_info=True)
        return False
    finally:
        db.close()

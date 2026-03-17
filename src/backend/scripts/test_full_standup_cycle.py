import sys
import os
import time
import uuid

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.db.database import SessionLocal
from src.backend.services.standup_manager import StandupManager
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.task import Task

def test_full_cycle():
    # Use owner for full control
    db_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        manager = StandupManager(db)
        project_id = "df940dce-e506-4878-b500-c2dba9b15920"
        channel_id = "C0AK49YQQJK"
        
        print("1. Triggering NEW Standup...")
        ts = manager.initiate_standup(project_id, channel_id)
        if not ts:
            print("Failed to initiate.")
            return
            
        # Get the standup ID
        standup = db.query(Standup).filter(Standup.message_ts == ts).first()
        standup_id = str(standup.id)
        print(f"Standup Initiated: {standup_id}")
        
        print("\n2. Simulating User Reply in Slack...")
        # Since we can't actually type in Slack, we'll wait 2 seconds for a human or just simulate the DB entry if we were testing processing
        print("Please reply to the NEW Slack thread now!")
        print("Suggested reply: '@ai-pm-bot I am finishing Agentic AI. Also assign Logo Design to Akshita.'")
        
        # In this automated test, we will actually simulate the Slack reply FETCHING
        # But SlackService.list_replies will call the API.
        # Let's wait for user to reply.
        
        for i in range(15):
            print(f"Waiting for reply... {15-i}s")
            time.sleep(1)
            
        print("\n3. Processing Replies...")
        manager.process_new_replies(standup_id)
        
        # Verify processing
        updates = db.query(StandupUpdate).filter(StandupUpdate.standup_id == standup_id).all()
        print(f"Updates Found: {len(updates)}")
        for u in updates:
            logs = db.query(StandupActionLog).filter(StandupActionLog.update_id == u.id).all()
            print(f"  - Logs for update {u.id}: {len(logs)}")
            for l in logs:
                print(f"    - {l.action_taken}")
                
        print("\n4. Finalizing...")
        manager.finalize_standup(standup_id)
        print("Finalized! Check Slack summary.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_full_cycle()

import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.db.database import SessionLocal
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog

def inspect_latest_standup():
    print("Connecting to DB...")
    db = SessionLocal()
    
    try:
        # 1. Get latest standup
        s = db.query(Standup).order_by(Standup.created_at.desc()).first()
        if not s:
            print("No standup found.")
            return
            
        print(f"--- Standup Session: {s.id} ---")
        print(f"Created At: {s.created_at}")
        print(f"Prompt Stored: {'Yes' if s.prompt else 'No'}")
        print(f"Summary Stored: {'Yes' if s.summary else 'No'}")
        
        # 2. Get updates
        updates = db.query(StandupUpdate).filter(StandupUpdate.standup_id == s.id).all()
        print(f"\nUpdates Found: {len(updates)}")
        for u in updates:
            print(f"  [{u.id}] Reply: {u.reply_text}")
            
            # 3. Get action logs for each update
            logs = db.query(StandupActionLog).filter(StandupActionLog.update_id == u.id).all()
            print(f"  Logs for this update: {len(logs)}")
            for l in logs:
                print(f"    - {l.action_taken}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_latest_standup()

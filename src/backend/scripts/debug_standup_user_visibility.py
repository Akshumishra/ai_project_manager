import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.db.database_standup import SessionStandup
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.user import User

def debug_standup_user():
    print("Connecting as standup_user...")
    db = SessionStandup()
    
    try:
        # Latest standup session
        s = db.query(Standup).order_by(Standup.created_at.desc()).first()
        if not s:
            print("No standup found.")
            return
            
        print(f"--- Visible Standup Session: {s.id} ---")
        
        # Get updates
        updates = db.query(StandupUpdate).filter(StandupUpdate.standup_id == s.id).all()
        print(f"Visible Updates Found: {len(updates)}")
        for u in updates:
            print(f"  Update: {u.reply_text}")
            
            # Action logs
            logs = db.query(StandupActionLog).filter(StandupActionLog.update_id == u.id).all()
            print(f"  Visible Logs: {len(logs)}")
            for l in logs:
                print(f"    - {l.action_taken}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_standup_user()

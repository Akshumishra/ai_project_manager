import sys
import os
import uuid
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.services.standup_manager import StandupManager

from src.backend.db.database_standup import SessionStandup

def reproduce_500():
    print("Connecting to DB as standup_user...")
    db = SessionStandup()
    
    try:
        manager = StandupManager(db)
        project_id = "b1389d5d-c3f9-481d-8749-492d9c559ed5"
        channel_id = "C0AL8G1T2UR"
        
        print(f"Attempting to initiate standup for {project_id}...")
        ts = manager.initiate_standup(project_id, channel_id)
        
        if ts:
            print(f"SUCCESS! TS: {ts}")
        else:
            print("FAILURE: initiate_standup returned None. Check logs (or previous output).")
            
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    reproduce_500()

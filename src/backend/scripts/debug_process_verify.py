import sys
import os
import uuid
import json
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.services.standup_manager import StandupManager
from src.backend.db.database import SessionLocal
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog

def debug_process():
    print("Connecting as OWNER to verify logic...")
    # Use owner URL
    db_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        manager = StandupManager(db)
        standup_id = "4a0e8206-75be-48e3-8e6b-bcfda6898599"
        
        print(f"Checking status for standup {standup_id}...")
        
        # 1. Clear existing logs for these updates to test fresh
        updates = db.query(StandupUpdate).filter(StandupUpdate.standup_id == standup_id).all()
        for u in updates:
            print(f"Clearing logs for update {u.id}...")
            db.query(StandupActionLog).filter(StandupActionLog.update_id == u.id).delete()
        db.commit()

        # 2. Re-process each update
        for u in updates:
            print(f"\nRe-processing reply: {u.reply_text}")
            
            # Get member name for AI
            from src.backend.model.user import User
            user_name = u.user.name if u.user else "Developer"
            
            # AI Parsing
            print("Calling AI Agent...")
            active_tasks = manager.generator.fetch_active_tasks(str(u.standup.project_id))
            flat_tasks = []
            for m_tasks in active_tasks.values():
                flat_tasks.extend(m_tasks)
            
            parsed = manager.agent.parse_reply(user_name, u.reply_text, flat_tasks)
            print(f"AI Parsed: {len(parsed.updates)} updates, {len(parsed.new_tasks)} new tasks")
            
            # Apply
            print("Applying updates...")
            manager._apply_parsed_updates(u.id, parsed)
            db.commit()
            
            # Verify logs
            logs = db.query(StandupActionLog).filter(StandupActionLog.update_id == u.id).all()
            print(f"Action Logs Created: {len(logs)}")
            for l in logs:
                print(f"  - {l.action_taken}")
                
    except Exception as e:
        print(f"OUTER CRASH: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_process()

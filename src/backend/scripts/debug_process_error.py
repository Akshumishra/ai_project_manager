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

def debug_process():
    print("Connecting as app_user (to read data)...")
    db = SessionLocal()
    
    try:
        manager = StandupManager(db)
        # Latest standup session
        standup_id = "4a0e8206-75be-48e3-8e6b-bcfda6898599"
        
        print(f"Triggering processing for standup {standup_id}...")
        
        # Manually trigger the reply processing logic to see the output
        from src.backend.model.standup import Standup
        standup = db.query(Standup).get(standup_id)
        replies = manager.slack_service.list_replies(standup.slack_channel_id, standup.message_ts)
        
        for reply in replies[1:]:
            user_slack_id = reply.get("user")
            text = reply.get("text")
            print(f"\nProcessing reply from {user_slack_id}: {text}")
            
            # Identify member
            from src.backend.model.project import ProjectMember
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == standup.project_id,
                ProjectMember.slack_id == user_slack_id
            ).first()
            
            if not member:
                print("Member not found.")
                continue
                
            from src.backend.model.user import User
            user = db.query(User).get(member.user_id)
            user_name = user.name if user else "Developer"
            
            # AI Parsing
            print("Calling AI Agent...")
            active_tasks = manager.generator.fetch_active_tasks(str(standup.project_id))
            flat_tasks = []
            for m_tasks in active_tasks.values():
                flat_tasks.extend(m_tasks)
                
            parsed = manager.agent.parse_reply(user_name, text, flat_tasks)
            print("--- AI Parsed Result ---")
            print(json.dumps(parsed.dict(), indent=2))
            
    except Exception as e:
        print(f"OUTER CRASH: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_process()

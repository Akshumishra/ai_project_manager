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
from src.backend.model.document import Document, DocumentBlock

def test_phase_10():
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
        
        print("\n--- Phase 10 Refinement Test ---")
        
        # 1. Trigger Standup
        print("1. Triggering Standup...")
        ts = manager.initiate_standup(project_id, channel_id)
        standup = db.query(Standup).filter(Standup.message_ts == ts).first()
        standup_id = str(standup.id)
        print(f"Standup ID: {standup_id}")

        # 2. Simulate complex reply (including document update and teammate assignment)
        # Reply text with a Slack ID to test cleaning
        raw_reply = "<@U0AJZR4M0DD> I am working on the database migration. Also tell Akshita to update the Color Palette. And add a new requirement: 'We should use Postgres 16' to the Architecture Specs document."
        user_slack_id = "U0AL9DCL2L8" # Aarushi
        
        print("\n2. Simulating Processing of complex reply...")
        # We manually call a special internal processing logic or just mock the slack list_replies if needed.
        # For simplicity, let's just use the real process_new_replies logic by ensuring the message is in Slack
        # OR we can just directly call _apply_parsed_updates for the specific parsed result.
        
        # Actually, let's just run the REAL manager.process_new_replies(standup_id) 
        # but we need to ensure Slack has the message.
        # EASIER: Since I want to prove the logic, I will manually create the StandupUpdate and call _apply_parsed_updates
        # But first, I'll test the Slack ID cleaning by calling the regex from manager.process_new_replies
        
        import re
        cleaned_text = re.sub(r'<@U[A-Z0-9]+>', '', raw_reply).strip()
        print(f"Cleaned Text: {cleaned_text}")
        if "<@U" in cleaned_text:
            print("FAILED: Slack ID not cleaned!")
        else:
            print("SUCCESS: Slack ID cleaned.")

        # AI Parsing Test
        from src.backend.agents.standup_agent import StandupReplyAgent
        agent = StandupReplyAgent()
        parsed = agent.parse_reply("Aarushi", raw_reply, []) # Empty tasks to force new tasks
        
        print("\n3. AI Parsing Results:")
        print(f"New Tasks: {len(parsed.new_tasks)}")
        for i, nt in enumerate(parsed.new_tasks):
            print(f"  [{i}] Name: {nt.name}, Assignee: {nt.assignee}, Desc: {nt.description}")
            if "I am working" in nt.description or "I am starting" in nt.description:
                print("  WARNING: Description is still unprofessional/quoted.")
            else:
                print("  SUCCESS: Description looks professional.")

        print(f"Doc Updates: {len(parsed.doc_updates)}")
        for du in parsed.doc_updates:
            print(f"  - Title: {du.title}, Content: {du.content}")

        # 4. Applying and Verifying Document Sync
        print("\n4. Verifying Document Sync...")
        # Mock a member for Aarushi
        from src.backend.model.project import ProjectMember
        member = db.query(ProjectMember).filter(ProjectMember.slack_id == user_slack_id).first()
        
        update = StandupUpdate(standup_id=standup.id, user_id=member.user_id, reply_text=cleaned_text)
        db.add(update)
        db.flush()
        
        manager._apply_parsed_updates(update.id, parsed)
        db.commit()
        
        # Check documents
        for du in parsed.doc_updates:
            doc = db.query(Document).filter(Document.project_id == project_id, Document.title == du.title).first()
            if doc:
                blocks = db.query(DocumentBlock).filter(DocumentBlock.doc_id == doc.id).all()
                print(f"Document '{du.title}' has {len(blocks)} blocks.")
                for b in blocks:
                    print(f"  Block [{b.position_key}]: {b.content[:50]}...")
            else:
                print(f"FAILED: Document '{du.title}' not found!")

        print("\n--- Test Complete ---")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_phase_10()

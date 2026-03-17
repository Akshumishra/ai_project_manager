import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.db.database_standup import SessionStandup
from src.backend.services.standup_manager import StandupManager
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.task import Task
from src.backend.model.task_log import TaskLog
from src.backend.model.document import Document, DocumentBlock
from sqlalchemy import text

def verify_phase_13():
    db = SessionStandup()
    manager = StandupManager(db)
    sid = '1b5e53dc-ad4b-412c-ab0f-7eed3f2a3153'
    pid = 'df940dce-e506-4878-b500-c2dba9b15920'
    
    print("--- Phase 13 Verification ---")
    
    # 1. Simulating complex reply with bots and formatting
    print("\n1. Simulating complex reply with bots and formatting...")
    # NOTE: In a real test, this would come from Slack. Here we are testing the processing logic.
    # We'll need to mock/stub the Slack reply for the manager to 'see' it, 
    # but the simplest way to test the logic is to let the manager fetch from Slack 
    # and we verify the transformations.
    
    print(f"Triggering processing for standup {sid}...")
    manager.process_new_replies(sid)
    db.commit()
    
    # 2. Verifying Data Cleaning
    print("\n2. Verifying Data Cleaning...")
    update = db.query(StandupUpdate).filter(StandupUpdate.standup_id == sid).order_by(StandupUpdate.created_at.desc()).first()
    if update:
        print(f"Cleaned Text: {update.reply_text}")
        if '_' in update.reply_text or '<@' in update.reply_text:
            print("FAIL: Cleaning failed (mentions or underscores still present)")
        else:
            print("SUCCESS: Cleaning works.")
    else:
        print("FAIL: No update found.")

    # 3. Verifying Tasks & Logs
    print("\n3. Verifying Tasks & Logs...")
    tasks = db.query(Task).filter(Task.project_id == pid).order_by(Task.created_at.desc()).limit(2).all()
    for t in tasks:
        print(f"Task: {t.name}, Deadline: {t.deadline}")
        logs = db.query(TaskLog).filter(TaskLog.task_id == t.id).all()
        print(f"  Logs: {len(logs)}")
        for l in logs:
            print(f"   - {l.log}")
            
    # 4. Verifying Documents
    print("\n4. Verifying Documents...")
    # The reply mentioned 'Architecture Docs' (case insensitive search test)
    doc = db.query(Document).filter(Document.project_id == pid, Document.title.ilike('%Architecture%')).first()
    if doc:
        print(f"Doc: {doc.title}")
        block = db.query(DocumentBlock).filter(DocumentBlock.doc_id == doc.id).order_by(DocumentBlock.position_key.desc()).first()
        if block:
            print(f"  Latest Block Content: {block.content[:100]}...")
            print(f"  Last Edited By: {block.last_edited_by}")
            if block.last_edited_by:
                print("SUCCESS: last_edited_by is set.")
            else:
                print("FAIL: last_edited_by is NOT set.")
        else:
            print("FAIL: No blocks found in doc.")
    else:
        print("FAIL: Architecture document not found in project.")

    db.close()

if __name__ == "__main__":
    verify_phase_13()

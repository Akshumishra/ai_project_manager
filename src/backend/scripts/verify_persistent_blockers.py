
import os
import sys
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.backend.services.standup_manager import StandupManager
from src.backend.model.task import Task, TaskStatus
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User
from src.backend.model.blocker import Blocker
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.agents.standup_agent import StandupParsedResponse, Blocker as PBlocker

# Database setup
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ai_manager_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def verify_refined_persistence():
    print("🚀 Starting Refined Blocker Persistence Verification...")
    
    manager = StandupManager(db)
    
    # 1. Setup: Find a project and a member
    project = db.query(Project).first()
    if not project:
        print("❌ No project found.")
        return
        
    member = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).first()
    user = db.query(User).get(member.user_id)
    
    # Clear active blockers
    db.query(Blocker).filter(Blocker.user_id == user.id, Blocker.resolved_at.is_(None)).update({Blocker.resolved_at: datetime.now(timezone.utc)})
    db.commit()

    # PHASE 1: Report a general blocker
    print("\n--- Phase 1: Reporting a general blocker ---")
    standup1 = Standup(project_id=project.id, message_ts="ts_" + str(uuid.uuid4()))
    db.add(standup1)
    db.flush()
    
    update1 = StandupUpdate(standup_id=standup1.id, user_id=user.id, reply_text="I am blocked by the API key.")
    db.add(update1)
    db.flush()
    
    parsed1 = StandupParsedResponse(
        updates=[],
        blockers=[PBlocker(reason="Blocked by API key", blocked_by="API key", impact="high", type="EXPLICIT")],
        sentiment="neutral"
    )
    
    manager._apply_parsed_updates(update1.id, parsed1)
    db.commit()
    
    blocker = db.query(Blocker).filter(Blocker.user_id == user.id, Blocker.resolved_at.is_(None)).first()
    if blocker and "API key" in blocker.reason:
        print(f"✅ Blocker created: {blocker.reason}")
    else:
        print("❌ Blocker creation failed.")
        return

    # PHASE 2: Omission test (Update without blocker)
    print("\n--- Phase 2: Omission test (Update without mentioning the blocker) ---")
    standup2 = Standup(project_id=project.id, message_ts="ts_" + str(uuid.uuid4()))
    db.add(standup2)
    db.flush()
    
    update2 = StandupUpdate(standup_id=standup2.id, user_id=user.id, reply_text="Just working on some other stuff today.")
    db.add(update2)
    db.flush()
    
    # NO blockers reported in this one
    parsed2 = StandupParsedResponse(
        updates=[],
        blockers=[],
        resolved_blockers=[],
        sentiment="neutral"
    )
    
    manager._apply_parsed_updates(update2.id, parsed2)
    db.commit()
    
    # Blocker should STILL BE ACTIVE (per user request)
    still_active = db.query(Blocker).get(blocker.id)
    if still_active.resolved_at is None:
        print("✅ Success: General blocker persisted even though not mentioned.")
    else:
        print("❌ Failure: General blocker was auto-resolved by omission.")

    # PHASE 3: Explicit resolution
    print("\n--- Phase 3: Explicit resolution ---")
    standup3 = Standup(project_id=project.id, message_ts="ts_" + str(uuid.uuid4()))
    db.add(standup3)
    db.flush()
    
    update3 = StandupUpdate(standup_id=standup3.id, user_id=user.id, reply_text="The API key is now fixed! No blockers.")
    db.add(update3)
    db.flush()
    
    # AI identifies resolution
    parsed3 = StandupParsedResponse(
        updates=[],
        blockers=[],
        resolved_blockers=["API key is fixed"],
        sentiment="positive"
    )
    
    manager._apply_parsed_updates(update3.id, parsed3)
    db.commit()
    
    # Blocker should be RESOLVED
    resolved = db.query(Blocker).get(blocker.id)
    if resolved.resolved_at is not None:
        print(f"✅ Success: Blocker resolved after explicit mention. (Resolved at: {resolved.resolved_at})")
    else:
        print("❌ Failure: Blocker remained active after explicit resolution mention.")

    print("\n🎉 Refined Verification Complete!")

if __name__ == "__main__":
    verify_refined_persistence()

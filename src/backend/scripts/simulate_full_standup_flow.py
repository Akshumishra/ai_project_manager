
import os
import sys
import uuid
import re
from datetime import datetime, timezone, timedelta
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

def simulate_flow():
    print("🚀 Starting End-to-End Standup & Blocker Flow Simulation...")
    manager = StandupManager(db)
    
    # --- SETUP ---
    project = db.query(Project).filter(Project.name == "AI Project Manager").first()
    if not project:
        print("❌ Project 'AI Project Manager' not found. Run seed_data.py first.")
        return
    
    member = db.query(User).filter(User.name == "Aarushi").first()
    if not member:
        print("❌ User 'Aarushi' not found.")
        return

    print(f"📋 Target: Project={project.name}, Member={member.name}")

    # Reset state for Aarushi
    db.query(Blocker).filter(Blocker.user_id == member.id, Blocker.resolved_at.is_(None)).update({Blocker.resolved_at: datetime.now(timezone.utc)})
    db.commit()

    # --- DAY 1: REPORTING ---
    print("\n--- [DAY 1] ---")
    print("Simulating morning standup prompt generation...")
    active_blockers = manager.generator.fetch_active_blockers(str(project.id))
    prompt = manager.generator.generate_standup_prompt(
        project.name,
        {},
        {},
        active_blockers=active_blockers,
        summary_insights=None
    )
    print("Morning Prompt (Partial):", prompt[:100] + "...")
    
    if "Member Blockers" not in prompt:
        print("✅ Correct: No active blockers yet.")

    print("\nAarushi replies with a blocker: 'I am blocked by hardware failure with my laptop. High impact.'")
    standup1 = Standup(project_id=project.id, message_ts="ts_day1_" + str(uuid.uuid4())[:8])
    db.add(standup1)
    db.flush()
    
    update1 = StandupUpdate(standup_id=standup1.id, user_id=member.id, reply_text="I am blocked by hardware failure with my laptop. High impact.")
    db.add(update1)
    db.flush()
    
    parsed1 = StandupParsedResponse(
        updates=[],
        blockers=[PBlocker(reason="Hardware failure with laptop", blocked_by="Laptop", impact="high", type="EXPLICIT")],
        sentiment="at_risk"
    )
    manager._apply_parsed_updates(update1.id, parsed1)
    db.commit()
    print("✅ Day 1 update processed. Blocker saved.")

    # --- DAY 2: PERSISTENCE (OMISSION) ---
    print("\n--- [DAY 2] ---")
    print("Generating next morning standup prompt...")
    active_blockers2 = manager.generator.fetch_active_blockers(str(project.id))
    prompt2 = manager.generator.generate_standup_prompt(
        project.name,
        {},
        {},
        active_blockers=active_blockers2,
        summary_insights=None
    )
    
    if "🚧 *Current Member Blockers:*" in prompt2 and "Hardware failure" in prompt2:
        print("✅ SUCCESS: Blocker persisted in morning prompt.")
    else:
        print("❌ FAILURE: Blocker missing from morning prompt.")
        return

    print("\nAarushi replies without mentioning the blocker: 'I worked on documentation.'")
    standup2 = Standup(project_id=project.id, message_ts="ts_day2_" + str(uuid.uuid4())[:8])
    db.add(standup2)
    db.flush()
    
    update2 = StandupUpdate(standup_id=standup2.id, user_id=member.id, reply_text="I worked on documentation.")
    db.add(update2)
    db.flush()
    
    parsed2 = StandupParsedResponse(
        updates=[],
        blockers=[],
        resolved_blockers=[],
        sentiment="neutral"
    )
    manager._apply_parsed_updates(update2.id, parsed2)
    db.commit()
    print("✅ Day 2 update processed (omission test).")

    # Verify still active
    b_check = db.query(Blocker).filter(Blocker.user_id == member.id, Blocker.resolved_at.is_(None)).first()
    if b_check and "Hardware failure" in b_check.reason:
        print("✅ SUCCESS: Blocker STILL ACTIVE in database (as requested by user).")
    else:
        print("❌ FAILURE: Blocker was incorrectly resolved by omission.")
        return

    # --- DAY 3: RESOLUTION ---
    print("\n--- [DAY 3] ---")
    print("Aarushi replies: 'My laptop is now fixed! No more blockers.'")
    standup3 = Standup(project_id=project.id, message_ts="ts_day3_" + str(uuid.uuid4())[:8])
    db.add(standup3)
    db.flush()
    
    update3 = StandupUpdate(standup_id=standup3.id, user_id=member.id, reply_text="My laptop is now fixed! No more blockers.")
    db.add(update3)
    db.flush()
    
    parsed3 = StandupParsedResponse(
        updates=[],
        blockers=[],
        resolved_blockers=["laptop is now fixed"],
        sentiment="positive"
    )
    manager._apply_parsed_updates(update3.id, parsed3)
    db.commit()
    print("✅ Day 3 update processed (explicit resolution).")

    # Verify resolved
    b_check_final = db.query(Blocker).filter(Blocker.id == b_check.id).first()
    if b_check_final.resolved_at is not None:
        print(f"✅ SUCCESS: Blocker resolved in database. (Resolved at: {b_check_final.resolved_at})")
    else:
        print("❌ FAILURE: Blocker is still active.")
        return

    print("\nNext morning prompt check...")
    active_blockers3 = manager.generator.fetch_active_blockers(str(project.id))
    prompt3 = manager.generator.generate_standup_prompt(
        project.name,
        {},
        {},
        active_blockers=active_blockers3,
        summary_insights=None
    )
    if "Hardware failure" not in prompt3:
        print("✅ SUCCESS: Blocker removed from morning prompt.")
    else:
        print("❌ FAILURE: Blocker still appearing in prompt.")

    print("\n🎉 Full Flow Simulation Successful!")

if __name__ == "__main__":
    try:
        simulate_flow()
    except Exception as e:
        print(f"❌ Error during simulation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

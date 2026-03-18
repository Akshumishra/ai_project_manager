import sys
import os
import uuid
import asyncio
from sqlalchemy import desc

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.backend.db.database_standup import SessionStandup
from src.backend.model.standup import Standup
from src.backend.model.project import ProjectMember, Project
from src.backend.model.user import User
from src.backend.model.standup_update import StandupUpdate
from src.backend.services.standup_manager import StandupManager

async def simulate_reply_behavior(reply_text: str, user_name: str = "Aarushi"):
    db = SessionStandup()
    try:
        manager = StandupManager(db)
        
        # 1. Find the latest standup for the project
        project = db.query(Project).filter(Project.name == "AI Project Manager").first()
        if not project:
            print("Project 'AI Project Manager' not found.")
            return
            
        standup = db.query(Standup).filter(Standup.project_id == project.id).order_by(desc(Standup.created_at)).first()
        if not standup:
            print(f"No standup found for project {project.name}. Run test_scheduler_jobs.py first.")
            return
            
        print(f"--- Simulating reply for Standup {standup.id} ---")
        print(f"User: {user_name}")
        print(f"Reply: \"{reply_text}\"")

        # 2. Find the project member
        member = db.query(ProjectMember).join(User).filter(
            ProjectMember.project_id == project.id,
            User.name == user_name
        ).first()
        
        if not member:
            print(f"Member '{user_name}' not found in project '{project.name}'.")
            return

        # 3. Simulate getting information for the AI agent
        # We'll use the manager's logic but feed it our manual reply
        # fetch_active_tasks returns (grouped_tasks, overdue_tasks, suggestions)
        active_tasks, _, suggestions = manager.generator.fetch_active_tasks(str(project.id))
        
        # Flatten tasks for context
        flat_tasks = []
        for m_tasks in active_tasks.values():
            flat_tasks.extend(m_tasks)
        for s_tasks in suggestions.values():
            flat_tasks.extend(s_tasks)
            
        member_names = [u.name for u in db.query(User).join(ProjectMember).filter(ProjectMember.project_id == project.id).all()]
        
        # 4. Parse the reply using the AI Agent
        print("\n🤖 AI parsing the reply...")
        parsed = manager.agent.parse_reply(
            user_name=user_name,
            reply_text=reply_text,
            active_tasks=flat_tasks,
            team_members=member_names
        )
        
        print(f"   Sentiment: {parsed.sentiment}")
        print(f"   Updates identified: {len(parsed.updates)}")
        for up in parsed.updates:
            print(f"   - Task: {up.task_title} -> {up.new_status}")

        # 5. Create the StandupUpdate record
        update = StandupUpdate(
            standup_id=standup.id,
            user_id=member.user_id,
            reply_text=reply_text,
            slack_ts="manual_sim_" + str(uuid.uuid4())[:8]
        )
        db.add(update)
        db.flush()

        # 6. Apply the parsed updates to the database
        print("\n💾 Applying updates to tasks...")
        manager._apply_parsed_updates(update.id, parsed)
        db.commit()

        # 7. Generate and Send Standup Summary (Evening Job logic)
        print("\n📝 Generating standup summary...")
        summary_ts = manager.finalize_standup(str(standup.id))
        
        if summary_ts:
            print(f"\n✨ SUCCESS: Standup finalized and summary posted to Slack (TS: {summary_ts})")
        else:
            print("\n⚠️ Finalization completed but no summary TS returned (check logs for errors).")

    except Exception as e:
        print(f"❌ Error during simulation: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reply = "I'll do Task 18 today. Also, I finished Task 1."
    if len(sys.argv) > 1:
        reply = " ".join(sys.argv[1:])
    
    asyncio.run(simulate_reply_behavior(reply))

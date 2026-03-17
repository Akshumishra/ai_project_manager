import sys
import os
import uuid
import json
from unittest.mock import MagicMock, patch
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.services.standup_manager import StandupManager
from src.backend.model.task import Task
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.project import Project, ProjectMember

def verify_flow():
    # Use the main DATABASE_URL (which we'll flip to postgres in the command)
    engine = create_engine(Config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("--- Starting Robust End-to-End Verification ---")
        
        # 1. Find valid test data
        member_row = db.query(ProjectMember).first()
        if not member_row:
            print("Error: No ProjectMember found in database. Please run insert_dummy_data.py first.")
            return
            
        project_id = member_row.project_id
        user_id = member_row.user_id
        slack_id = member_row.slack_id
        
        project = db.query(Project).get(project_id)
        project_name = project.name if project else "Test Project"
        
        print(f"Verified Test Context: Project='{project_name}' ({project_id}), Member UserID={user_id}, SlackID={slack_id}")

        # Ensure a task exists for this project to update
        task = db.query(Task).filter(Task.project_id == project_id).first()
        if not task:
            # Create a dummy task just for the test if it doesn't exist
            task = Task(name="Verification Task", project_id=project_id, project_member_id=member_row.id, status="ToDo")
            db.add(task)
            db.commit()
            db.refresh(task)
        
        task_id_str = str(task.id)

        # 2. Mock External Services
        with patch('src.backend.services.slack_service.requests.post') as mock_post, \
             patch('src.backend.services.slack_service.requests.get') as mock_get, \
             patch('src.backend.agents.standup_agent.ChatOpenAI') as mock_llm:
            
            # Setup Mocks
            mock_post.return_value.json.return_value = {"ok": True, "ts": "123.456"}
            mock_post.return_value.status_code = 200
            
            # Simulated Slack Replies
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "ok": True,
                "messages": [
                    {"text": "Prompt", "ts": "123.456", "user": "BOT"},
                    {"text": f"I worked on the API. {task.name} is now InProgress. No blockers.", "ts": "123.789", "user": slack_id}
                ]
            }
            
            # Simulated LangChain AI Response
            mock_chain = MagicMock()
            # We mock the Pydantic response object
            from src.backend.agents.standup_agent import StandupParsedResponse, TaskUpdate
            mock_response = StandupParsedResponse(
                updates=[
                    TaskUpdate(task_id=task_id_str, task_name=task.name, new_status="InProgress", comment="Working on API")
                ],
                blockers=[],
                new_tasks=[],
                sentiment="positive"
            )
            mock_chain.invoke.return_value = mock_response
            mock_llm.return_value.with_structured_output.return_value = mock_chain

            # 3. Execution using the Manager
            # Note: In the real app, manager would use STANDUP_DATABASE_URL, 
            # but for this verification script we inject the current session 'db'
            manager = StandupManager(db)
            # Monkeypatch the manager's db to use our 'db' session (which has owner rights here)
            manager.db = db
            manager.generator.db = db

            print(f"Step 1: Initiating standup for '{project_name}'...")
            ts = manager.initiate_standup(str(project_id), "C12345")
            print(f"Standup initiated with TS: {ts}")
            
            # Find the created standup record
            standup = db.query(Standup).filter(Standup.message_ts == ts).first()
            if not standup:
                print("FAILURE: Standup record not found in DB.")
                return
            
            print(f"Step 2: Processing replies for standup {standup.id}...")
            manager.process_new_replies(str(standup.id))
            
            # Verify update recorded
            update = db.query(StandupUpdate).filter(StandupUpdate.standup_id == standup.id).first()
            if update:
                print(f"SUCCESS: Raw update recorded: '{update.reply_text}'")
            else:
                print("FAILURE: No update recorded in StandupUpdate table.")
                
            # Verify task was updated
            db.refresh(task)
            if task.status.value == "InProgress":
                print(f"SUCCESS: Task '{task.name}' status updated to InProgress.")
            else:
                print(f"FAILURE: Task status remained {task.status.value}.")

            print("Step 3: Finalizing standup...")
            manager.finalize_standup(str(standup.id))
            
            # Verify summary stored
            db.refresh(standup)
            if standup.summary:
                print(f"SUCCESS: Summary generated and stored: {standup.summary[:40]}...")
            else:
                print("FAILURE: No summary generated.")

        print("--- Verification Complete Successfully ---")

    except Exception as e:
        print(f"Verification Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_flow()

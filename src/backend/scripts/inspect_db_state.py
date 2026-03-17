
import sys
import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.backend.config import Config
from src.backend.model.project import Project, ProjectSlackDetail
from src.backend.model.task import Task

def check_db():
    database_url = Config.STANDUP_DATABASE_URL or "postgresql://postgres:password123@localhost:5432/ai_manager_db"
    if "app_user:test123" in database_url:
        print("💡 Detected app_user. Switching to postgres (owner) to bypass RLS for inspection...")
        database_url = database_url.replace("app_user:test123", "postgres:password123")
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("--- Projects ---")
        projects = db.query(Project).all()
        for p in projects:
            print(f"ID: {p.id}, Name: {p.name}")
            
        print("\n--- Project Slack Details ---")
        details = db.query(ProjectSlackDetail).all()
        if not details:
            print("No Slack details found!")
        for d in details:
            print(f"Project ID: {d.project_id}, Channel ID: {d.channel_id}")
            
        print("\n--- Tasks ---")
        task_count = db.query(Task).count()
        print(f"Total tasks: {task_count}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_db()


import os
import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.backend.model.project import Project, ProjectSlackDetail, ProjectMember
from src.backend.model.user import User
from src.backend.model.user_detail import UserDetail

# Database setup
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ai_manager_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def setup_recrude_project():
    print("🚀 Setting up 'recrude' project...")
    
    # 1. Check if project already exists
    project = db.query(Project).filter(Project.name == "recrude").first()
    
    # Get a creator ID (just pick the first user or Aarushi)
    aarushi = db.query(User).filter(User.name == "Aarushi").first()
    if not aarushi:
        print("❌ Aarushi user not found.")
        return

    if not project:
        project = Project(
            name="recrude",
            description="New recruitment and project management tool.",
            status="active",
            created_by=aarushi.id
        )
        db.add(project)
        db.flush()
        print(f"✅ Created project 'recrude' (ID: {project.id})")
    else:
        print(f"ℹ️ Project 'recrude' already exists (ID: {project.id})")

    # 2. Setup Slack Details
    slack_detail = db.query(ProjectSlackDetail).filter(ProjectSlackDetail.project_id == project.id).first()
    if not slack_detail:
        slack_detail = ProjectSlackDetail(
            project_id=project.id,
            channel_id="C0ALTNG8HQU",
            workspace_id="T0AK49XGZ" # Hardcoded based on existing data if needed, or left null
        )
        db.add(slack_detail)
        print(f"✅ Linked project to channel C0ALTNG8HQU")
    else:
        slack_detail.channel_id = "C0ALTNG8HQU"
        print(f"✅ Updated project channel to C0ALTNG8HQU")

    # 3. Add Members
    members_to_add = ["Aarushi", "Akshita"]
    for member_name in members_to_add:
        user = db.query(User).filter(User.name == member_name).first()
        if user:
            # Check if already a member
            existing = db.query(ProjectMember).filter(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id
            ).first()
            
            if not existing:
                # Get slack_id from UserDetail
                detail = db.query(UserDetail).filter(UserDetail.user_id == user.id).first()
                slack_id = detail.slack_id if detail else None
                
                member = ProjectMember(
                    project_id=project.id,
                    user_id=user.id,
                    slack_id=slack_id
                )
                db.add(member)
                print(f"✅ Added {member_name} to project 'recrude'")
            else:
                print(f"ℹ️ {member_name} is already a member of 'recrude'")
        else:
            print(f"⚠️ User {member_name} not found.")

    db.commit()
    print("🎉 Setup complete!")

if __name__ == "__main__":
    try:
        setup_recrude_project()
    except Exception as e:
        print(f"❌ Error setting up project: {e}")
        db.rollback()
    finally:
        db.close()

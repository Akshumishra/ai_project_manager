import sys
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine

# Add the project root to sys.path
sys.path.append(os.getcwd())

from src.backend.db.database import SessionLocal, create_tables
from src.backend.model import (
    User, UserDetail, Project, ProjectSlackDetail, ProjectMember,
    RequirementChat, Task, TaskStatus, TaskCategory, TaskPriority, TaskComplexity,
    Blocker, Standup, StandupUpdate, Document, DocumentBlock
)
from src.backend.config import Config
import uuid
from sqlalchemy.orm import sessionmaker

def insert_dummy_data():
    # Use OWNER (postgres) credentials to bypass RLS during seeding
    # Administrative seeding is often blocked by RLS for standard app users
    database_url = Config.DATABASE_URL or "sqlite:///./app.db"
    if "app_user:test123" in database_url:
        print("💡 Detected app_user. Switching to postgres (owner) to bypass RLS for seeding...")
        database_url = database_url.replace("app_user:test123", "postgres:password123")
    
    engine = create_engine(database_url)
    AdminSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = AdminSession()
    
    try:
        print("Ensuring database tables exist...")
        from src.backend.db.database import Base
        print(f"DEBUG: Active models in Base.metadata: {list(Base.metadata.tables.keys())}")
        create_tables()
        print("Starting comprehensive dummy data insertion...")
        
        # 1. Create Users
        users_data = [
            {"name": "Aarushi", "email": "aarushi@gkmit.co", "slack_id": "U0AL9DCL2L8"},
            {"name": "Akshita", "email": "akshita@gkmit.co", "slack_id": "U0AKEJAF962"},
            {"name": "Rudraksh", "email": "rudraksh@gkmit.co", "slack_id": "U0ALE6XJEU8"},
        ]
        
        db_users = []
        for u in users_data:
            user = db.query(User).filter(User.email == u["email"]).first()
            if not user:
                user = User(name=u["name"], email=u["email"])
                db.add(user)
                db.flush()
                print(f"Created user: {u['name']}")
            else:
                print(f"User {u['name']} already exists.")
            
            detail = db.query(UserDetail).filter(UserDetail.user_id == user.id).first()
            if not detail:
                detail = UserDetail(user_id=user.id, slack_id=u["slack_id"])
                db.add(detail)
                print(f"Created user detail for: {u['name']}")
            else:
                detail.slack_id = u["slack_id"]
                print(f"Updated user detail for: {u['name']}")
            
            db_users.append(user)
            
        # 2. Create Projects
        projects_data = [
            {"name": "AI Project Manager", "channel_id": "C0AK49YQQJK", "desc": "Internal tool for managing AI projects and Slack integrations."},
            {"name": "AI Tutor", "channel_id": "C0AL8G1T2UR", "desc": "Educational platform leveraging AI to provide personalized tutoring."},
        ]
        
        for p_data in projects_data:
            project = db.query(Project).filter(Project.name == p_data["name"]).first()
            if not project:
                project = Project(
                    name=p_data["name"], 
                    description=p_data["desc"],
                    status="active",
                    created_by=db_users[0].id # Aarushi
                )
                db.add(project)
                db.flush()
                print(f"Created project: {p_data['name']}")
            else:
                print(f"Project {p_data['name']} already exists.")
            
            # 3. Project Slack Details
            slack_detail = db.query(ProjectSlackDetail).filter(ProjectSlackDetail.project_id == project.id).first()
            if not slack_detail:
                slack_detail = ProjectSlackDetail(
                    project_id=project.id, 
                    channel_id=p_data["channel_id"],
                    workspace_id="T0123456789" # Mock workspace ID
                )
                db.add(slack_detail)
                print(f"Created slack detail for project: {p_data['name']}")
            else:
                slack_detail.channel_id = p_data["channel_id"]
                print(f"Updated slack detail for project: {p_data['name']}")
            
            # 4. Project Members & Assignees
            project_members = []
            for user in db_users:
                slack_id = next(u["slack_id"] for u in users_data if u["email"] == user.email)
                member = db.query(ProjectMember).filter(
                    ProjectMember.project_id == project.id, 
                    ProjectMember.user_id == user.id
                ).first()
                
                if not member:
                    member = ProjectMember(project_id=project.id, user_id=user.id, slack_id=slack_id)
                    db.add(member)
                    db.flush()
                    print(f"Added member {user.name} to project {p_data['name']}")
                else:
                    member.slack_id = slack_id
                    print(f"Updated member {user.name} slack_id in project {p_data['name']}")
                project_members.append(member)
 
            # 5. Requirement Chats
            chat = db.query(RequirementChat).filter(RequirementChat.project_id == project.id).first()
            if not chat:
                chats = [
                    RequirementChat(project_id=project.id, role="user", content="We need a way to track project progress via Slack.", project_member_id=project_members[0].id),
                    RequirementChat(project_id=project.id, role="assistant", content="I can set up a daily digest service for your Slack channels. Which channels should I monitor?")
                ]
                db.add_all(chats)
                print(f"Added requirement chats for project: {p_data['name']}")
 
            # 6. Tasks
            task = db.query(Task).filter(Task.project_id == project.id).first()
            if not task:
                if p_data["name"] == "AI Project Manager":
                    tasks = [
                        Task(
                            title="Initial Architecture Design", label=1, project_id=project.id, 
                            description="Define the core modules and database schema.", status=TaskStatus.COMPLETED, 
                            assignee_id=project_members[0].id, deadline=datetime(2026, 3, 10, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.DATABASE, priority=TaskPriority.HIGH
                        ),
                        Task(
                            title="Slack Integration Setup", label=2, project_id=project.id, 
                            description="Configure Bolt and handle incoming events.", status=TaskStatus.IN_PROGRESS, 
                            assignee_id=project_members[1].id, deadline=datetime(2026, 3, 25, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.HIGH, category=TaskCategory.BACKEND, priority=TaskPriority.HIGH
                        ),
                        Task(
                            title="User Testing Phase 1", label=3, project_id=project.id, 
                            description="Gather feedback from initial users.", status=TaskStatus.TODO, 
                            assignee_id=project_members[2].id, deadline=datetime(2026, 3, 30, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.LOW, category=TaskCategory.QA, priority=TaskPriority.LOW
                        ),
                        Task(
                            title="Implement OAuth Flow", label=4, project_id=project.id, 
                            description="Secure user authentication with Slack OAuth.", status=TaskStatus.BLOCKED, 
                            assignee_id=project_members[0].id, deadline=datetime(2026, 4, 5, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.HIGH, category=TaskCategory.SECURITY, priority=TaskPriority.HIGH
                        ),
                        Task(
                            title="CI/CD Pipeline Setup", label=5, project_id=project.id, 
                            description="Automate deployment with GitHub Actions.", status=TaskStatus.TODO, 
                            assignee_id=None, deadline=datetime(2026, 4, 10, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.DEVOPS, priority=TaskPriority.MEDIUM
                        ),
                        Task(
                            title="Frontend Dashboard Mockups", label=6, project_id=project.id, 
                            description="Design the user interface for the project dashboard.", status=TaskStatus.TODO, 
                            assignee_id=project_members[1].id, deadline=datetime(2026, 3, 28, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.FRONTEND, priority=TaskPriority.MEDIUM
                        ),
                        Task(
                            title="AI Model Fine-tuning", label=7, project_id=project.id, 
                            description="Optimize GPT models for project management queries.", status=TaskStatus.TODO, 
                            assignee_id=project_members[2].id, deadline=datetime(2026, 4, 15, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.HIGH, category=TaskCategory.AI_ML, priority=TaskPriority.HIGH
                        ),
                        Task(
                            title="API Rate Limiting", label=8, project_id=project.id, 
                            description="Prevent abuse by implementing rate limits.", status=TaskStatus.TODO, 
                            assignee_id=project_members[0].id, deadline=datetime(2026, 4, 20, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.BACKEND, priority=TaskPriority.MEDIUM
                        ),
                        Task(
                            title="Documentation Audit", label=9, project_id=project.id, 
                            description="Review and update all technical documentation.", status=TaskStatus.TODO, 
                            assignee_id=project_members[1].id, deadline=datetime(2026, 4, 25, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.LOW, category=TaskCategory.QA, priority=TaskPriority.LOW
                        ),
                        Task(
                            title="Database Migration Script", label=10, project_id=project.id, 
                            description="Script to migrate legacy task data.", status=TaskStatus.COMPLETED, 
                            assignee_id=project_members[2].id, deadline=datetime(2026, 3, 16, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.DATABASE, priority=TaskPriority.MEDIUM
                        )
                    ]
                else: # AI Tutor tasks
                    tasks = [
                        Task(
                            title="Syllabus Parsing AI", label=1, project_id=project.id, 
                            description="Develop AI to parse university syllabi into structured schedules.", status=TaskStatus.COMPLETED, 
                            assignee_id=project_members[0].id, deadline=datetime(2026, 3, 5, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.HIGH, category=TaskCategory.AI_ML, priority=TaskPriority.HIGH
                        ),
                        Task(
                            title="Automatic Quiz Generator", label=2, project_id=project.id, 
                            description="Create a backend service to generate quizzes from lesson content.", status=TaskStatus.IN_PROGRESS, 
                            assignee_id=project_members[1].id, deadline=datetime(2026, 3, 20, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.BACKEND, priority=TaskPriority.MEDIUM
                        ),
                        Task(
                            title="Student Progress Dashboard", label=3, project_id=project.id, 
                            description="Build a dashboard for students to track their learning goals.", status=TaskStatus.TODO, 
                            assignee_id=project_members[2].id, deadline=datetime(2026, 3, 28, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.FRONTEND, priority=TaskPriority.MEDIUM
                        ),
                        Task(
                            title="Database Scaling Strategy", label=4, project_id=project.id, 
                            description="Plan for handling 100k concurrent student users.", status=TaskStatus.TODO, 
                            assignee_id=project_members[0].id, deadline=datetime(2026, 4, 1, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.HIGH, category=TaskCategory.DATABASE, priority=TaskPriority.HIGH
                        ),
                        Task(
                            title="Education Data Security Audit", label=5, project_id=project.id, 
                            description="Ensure compliance with student privacy regulations.", status=TaskStatus.TODO, 
                            assignee_id=None, deadline=datetime(2026, 4, 10, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.HIGH, category=TaskCategory.SECURITY, priority=TaskPriority.HIGH
                        ),
                        Task(
                            title="Load Testing for Video Stream", label=6, project_id=project.id, 
                            description="Simulate peak load on tutoring video sessions.", status=TaskStatus.TODO, 
                            assignee_id=project_members[1].id, deadline=datetime(2026, 4, 15, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.QA, priority=TaskPriority.MEDIUM
                        ),
                        Task(
                            title="Production Cloud Deployment", label=7, project_id=project.id, 
                            description="Deploy the platform to AWS production environment.", status=TaskStatus.BLOCKED, 
                            assignee_id=None, deadline=datetime(2026, 4, 20, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.HIGH, category=TaskCategory.DEVOPS, priority=TaskPriority.HIGH
                        ),
                        Task(
                            title="Natural Language Feedback Engine", label=8, project_id=project.id, 
                            description="Implement AI engine for generating student feedback.", status=TaskStatus.TODO, 
                            assignee_id=project_members[2].id, deadline=datetime(2026, 4, 25, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.HIGH, category=TaskCategory.AI_ML, priority=TaskPriority.HIGH
                        ),
                        Task(
                            title="Teacher Admin Panel", label=9, project_id=project.id, 
                            description="UI for teachers to manage courses and view student analytics.", status=TaskStatus.TODO, 
                            assignee_id=project_members[0].id, deadline=datetime(2026, 5, 1, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.FRONTEND, priority=TaskPriority.MEDIUM
                        ),
                        Task(
                            title="API v2 Implementation", label=10, project_id=project.id, 
                            description="Refactor API for third-party LMS integration.", status=TaskStatus.TODO, 
                            assignee_id=project_members[1].id, deadline=datetime(2026, 5, 5, tzinfo=timezone.utc), 
                            complexity=TaskComplexity.MEDIUM, category=TaskCategory.BACKEND, priority=TaskPriority.LOW
                        )
                    ]
                db.add_all(tasks)
                print(f"Added {len(tasks)} varied tasks for project: {p_data['name']}")

            # 7. Documents & Blocks
            doc = db.query(Document).filter(Document.project_id == project.id).first()
            if not doc:
                doc = Document(project_id=project.id, title="Project Specification", created_by=db_users[0].id)
                db.add(doc)
                db.flush()
                
                blocks = [
                    DocumentBlock(doc_id=doc.id, content=f"# {p_data['name']} Specification", position_key="001", type="heading"),
                    DocumentBlock(doc_id=doc.id, content=p_data["desc"], position_key="002", type="paragraph")
                ]
                db.add_all(blocks)
                print(f"Added documents and blocks for project: {p_data['name']}")
        
        db.commit()
        print("Comprehensive dummy data insertion script generated successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error preparing dummy data: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    insert_dummy_data()

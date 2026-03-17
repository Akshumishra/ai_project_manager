import sys
import os
from datetime import datetime, timedelta, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.db.database import SessionLocal
from src.backend.model.task import Task, TaskStatus, TaskComplexity, TaskPriority
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User
from src.backend.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def clear_standup_and_log_tables():
    """Clear standup-related tables and task logs, but keep tasks."""
    database_url = Config.DATABASE_URL or "sqlite:///./app.db"
    
    # Handle PostgreSQL URL replacement if needed
    if "app_user:test123" in database_url:
        print("💡 Detected app_user. Switching to postgres (owner) to bypass RLS for clearing...")
        database_url = database_url.replace("app_user:test123", "postgres:password123")
    
    engine = create_engine(database_url)
    
    tables = [
        "task_logs",
        "standup_action_logs",
        "standup_updates",
        "standups",
        "tasks"
    ]
    
    print("🧹 Clearing data from standup and task log tables...")
    
    with engine.begin() as conn:
        for table in tables:
            try:
                print(f"  Truncating {table}...")
                conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
            except Exception as e:
                # For SQLite, use DELETE instead of TRUNCATE
                if "TRUNCATE" in str(e) or "syntax error" in str(e).lower():
                    print(f"  Deleting from {table} (SQLite)...")
                    conn.execute(text(f"DELETE FROM {table}"))
                else:
                    raise e
    
    print("✅ Standup and log tables cleared.\n")

def populate_comprehensive_tasks():
    """Populate tasks table with comprehensive test data covering all scenarios."""
    database_url = Config.DATABASE_URL or "sqlite:///./app.db"
    if "app_user:test123" in database_url:
        database_url = database_url.replace("app_user:test123", "postgres:password123")
    
    engine = create_engine(database_url)
    AdminSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = AdminSession()
    
    try:
        # Get projects and members
        projects = db.query(Project).all()
        if not projects:
            print("❌ No projects found even with admin session. Please run insert_dummy_data.py first.")
            return
        
        print("📋 Populating tasks with comprehensive test data...\n")
        
        # Get all project members
        all_members = {}
        for project in projects:
            members = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
            for member in members:
                user = db.get(User, member.user_id)
                if user:
                    key = f"{project.id}_{user.name}"
                    if key not in all_members:
                        all_members[key] = {
                            'member': member,
                            'user': user,
                            'project': project
                        }
        
        if not all_members:
            print("❌ No project members found. Please run insert_dummy_data.py first.")
            return
        
        # Calculate dates
        today = datetime.now(timezone.utc)
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        last_week = today - timedelta(days=7)
        
        # Comprehensive task data covering all scenarios
        # Format: (project_name, user_name, task_name, status, deadline_days_offset, complexity, description)
        task_data = []
        
        for project in projects:
            project_members = [m for k, m in all_members.items() if m['project'].id == project.id]
            
            if not project_members:
                continue
            
            # Get first 3 members (or all if less than 3)
            members = project_members[:3]
            
            for member_info in members:
                user_name = member_info['user'].name
                member = member_info['member']
                
                if user_name == "Aarushi":
                    task_data.extend([
                        (project, member, "Core System Architecture Review", TaskStatus.IN_PROGRESS, 2, TaskComplexity.HIGH, "Final review of the core system modules."),
                        (project, member, "UI Design System Definition", TaskStatus.TODO, 3, TaskComplexity.MEDIUM, "Establishing the primary color palette and typography."),
                        (project, member, "Sprint Planning & Backlog Grooming", TaskStatus.TODO, 5, TaskComplexity.LOW, "Organizing upcoming user stories."),
                        (project, member, "Initial Stakeholder Presentation", TaskStatus.COMPLETED, -2, TaskComplexity.MEDIUM, "Presenting the project roadmap to stakeholders.")
                    ])
                elif user_name == "Akshita":
                    task_data.extend([
                        (project, member, "PostgreSQL Schema Optimization", TaskStatus.IN_PROGRESS, 4, TaskComplexity.HIGH, "Optimizing indexes and query performance."),
                        (project, member, "API Endpoint Documentation", TaskStatus.TODO, 6, TaskComplexity.MEDIUM, "Writing Swagger/OpenAPI docs for the new routes."),
                        (project, member, "Database Migration Logic", TaskStatus.IN_PROGRESS, 1, TaskComplexity.MEDIUM, "Developing the logic for automated schema updates."),
                        (project, member, "Basic User Authentication", TaskStatus.COMPLETED, -4, TaskComplexity.HIGH, "Implemented OAuth2 flow for the backend.")
                    ])
                elif user_name == "Rudraksh":
                    task_data.extend([
                        (project, member, "Comprehensive Security Audit", TaskStatus.BLOCKED, 8, TaskComplexity.HIGH, "Audit blocked by missing compliance checklist."),
                        (project, member, "End-to-End Testing Suite Setup", TaskStatus.IN_PROGRESS, 3, TaskComplexity.MEDIUM, "Setting up Playwright for integration tests."),
                        (project, member, "Frontend Component Library", TaskStatus.TODO, 10, TaskComplexity.MEDIUM, "Building reusable React components."),
                        (project, member, "CI/CD Pipeline Configuration", TaskStatus.COMPLETED, -1, TaskComplexity.HIGH, "Automated deployment to staging.")
                    ])
                else:
                    # Generic tasks for any other members
                    task_data.extend([
                        (project, member, f"{user_name}'s Feature Development", TaskStatus.TODO, 5, TaskComplexity.MEDIUM, f"General task for {user_name}"),
                        (project, member, f"{user_name}'s Ongoing Research", TaskStatus.IN_PROGRESS, 2, TaskComplexity.LOW, f"Discovery work for {user_name}")
                    ])
        
        # Create all tasks
        created_count = 0
        
        for project, member, task_title, status, deadline_offset, complexity, description in task_data:
            deadline = (today + timedelta(days=deadline_offset))
            
            task = Task(
                title=task_title,
                project_id=project.id,
                assignee_id=member.id,
                description=description,
                status=status,
                complexity=complexity,
                deadline=deadline
            )
            db.add(task)
            created_count += 1
        
        db.commit()
        
        # Print summary
        print(f"✅ Created {created_count} tasks across {len(projects)} projects\n")
        
        # Print breakdown by status
        for project in projects:
            print(f"📊 {project.name}:")
            for status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.COMPLETED]:
                count = db.query(Task).filter(
                    Task.project_id == project.id,
                    Task.status == status,
                    Task.deleted_at.is_(None)
                ).count()
                print(f"   {status.value.upper()}: {count} tasks")
            
            # Print breakdown by member
            print(f"   By Member:")
            for key, member_info in all_members.items():
                if member_info['project'].id == project.id:
                    user_name = member_info['user'].name
                    member = member_info['member']
                    todo_count = db.query(Task).filter(
                        Task.project_id == project.id,
                        Task.assignee_id == member.id,
                        Task.status == TaskStatus.TODO,
                        Task.deleted_at.is_(None)
                    ).count()
                    inprogress_count = db.query(Task).filter(
                        Task.project_id == project.id,
                        Task.assignee_id == member.id,
                        Task.status == TaskStatus.IN_PROGRESS,
                        Task.deleted_at.is_(None)
                    ).count()
                    blocked_count = db.query(Task).filter(
                        Task.project_id == project.id,
                        Task.assignee_id == member.id,
                        Task.status == TaskStatus.BLOCKED,
                        Task.deleted_at.is_(None)
                    ).count()
                    completed_count = db.query(Task).filter(
                        Task.project_id == project.id,
                        Task.assignee_id == member.id,
                        Task.status == TaskStatus.COMPLETED,
                        Task.deleted_at.is_(None)
                    ).count()
                    print(f"      {user_name}: TODO={todo_count}, IN_PROGRESS={inprogress_count}, BLOCKED={blocked_count}, COMPLETED={completed_count}")
            print()
        
        print("✅ Task population complete! Ready for comprehensive testing.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error populating tasks: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 Reset and Populate Tasks for Comprehensive Testing")
    print("=" * 60)
    print()
    
    # Step 1: Clear standup and log tables
    clear_standup_and_log_tables()
    
    # Step 2: Populate tasks
    populate_comprehensive_tasks()
    
    print()
    print("=" * 60)
    print("✅ All done! You can now test all scenarios:")
    print("   - Multiple tasks per person in each status")
    print("   - All status types: TODO, IN_PROGRESS, BLOCKED, COMPLETED")
    print("   - Tasks distributed across projects")
    print("=" * 60)

import sys
import os
from datetime import datetime, timedelta

# Add the project root to sys.path
sys.path.append(os.getcwd())

from src.backend.db.database import SessionLocal
from src.backend.model.task import Task, TaskStatus
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User

def insert_test_tasks():
    db = SessionLocal()
    try:
        # Get the first project
        project = db.query(Project).first()
        if not project:
            print("No project found in database.")
            return

        # Get members of this project
        members = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
        if not members:
            print(f"No members found for project {project.name}.")
            return

        print(f"Adding multi-task test data for project: {project.name}")

        # Assign multiple tasks to the first member to test grouping
        primary_member = members[0]
        
        test_tasks = [
            # In Progress tasks for primary member
            {"name": "Database Schema Optimization", "status": TaskStatus.IN_PROGRESS, "member": primary_member},
            {"name": "Frontend Refactoring", "status": TaskStatus.IN_PROGRESS, "member": primary_member},
            
            # TODO tasks for primary member
            {"name": "Implement Unit Tests", "status": TaskStatus.TODO, "member": primary_member},
            {"name": "Update User Docs", "status": TaskStatus.TODO, "member": primary_member},
        ]

        # Add tasks for other members if available
        if len(members) > 1:
            test_tasks.append({"name": "Slack Webhook Setup", "status": TaskStatus.IN_PROGRESS, "member": members[1]})
            test_tasks.append({"name": "Security Audit", "status": TaskStatus.TODO, "member": members[1]})

        for task_data in test_tasks:
            new_task = Task(
                title=task_data["name"],
                description=f"Automated test task for {task_data['name']}",
                status=task_data["status"],
                project_id=project.id,
                assignee_id=task_data["member"].id,
                deadline=datetime.now() + timedelta(days=7),
                complexity="Medium",
                label=1 # Need a label
            )
            db.add(new_task)
            print(f"Added task: {new_task.title} ({new_task.status.value}) assigned to member ID: {new_task.assignee_id}")

        db.commit()
        print("Successfully added multi-task test data.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    insert_test_tasks()


"""
Seed script: Creates 3 users, 3 projects, and adds all users as members.
Target DB: postgresql://postgres:password@localhost/testing_ai
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:password@localhost/testing_ai"

engine = create_engine(DATABASE_URL)
SessionFactory = sessionmaker(bind=engine)

import src.backend.model  # noqa – registers all ORM models
from src.backend.db.database import Base
from src.backend.model.user import User, UserStatus
from src.backend.model.project import Project, ProjectMember, ProjectStatus

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

USERS = [
    {"name": "Aarushi",   "email": "aarushi@gkmit.co",   "slack_id": "U0AL9DCL2L8"},
    {"name": "Akshita",   "email": "akshita@gkmit.co",   "slack_id": "U0AKEJAF962"},
    {"name": "Rudraksh",  "email": "rudraksh@gkmit.co",  "slack_id": "U0ALE6XJEU8"},
]

PROJECTS = [
    {"name": "AI Project Manager", "slack_channel_id": "C0AK49YQQJK"},
    {"name": "Tutor",              "slack_channel_id": "C0AL8G1T2UR"},
    {"name": "Recrude",            "slack_channel_id": "C0ALTNG8HQU"},
]

def seed():
    db = SessionFactory()
    from sqlalchemy.sql import func

    try:
        # 1. Upsert users
        user_objects = {}
        for u in USERS:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if existing:
                print(f"  User exists: {u['email']}")
                user_objects[u["email"]] = (existing, u["slack_id"])
            else:
                new_user = User(
                    name=u["name"],
                    email=u["email"],
                    password_hash=None,
                    status=UserStatus.ACTIVE,
                    is_verified=True,
                )
                db.add(new_user)
                db.flush()
                print(f"  Created user: {u['email']} (id={new_user.id})")
                user_objects[u["email"]] = (new_user, u["slack_id"])

        creator_user = user_objects["rudraksh@gkmit.co"][0]

        # 2. Upsert projects
        project_objects = []
        for p in PROJECTS:
            existing = db.query(Project).filter(
                Project.name == p["name"],
                Project.deleted_at.is_(None)
            ).first()
            if existing:
                if not existing.slack_channel_id:
                    existing.slack_channel_id = p["slack_channel_id"]
                    print(f"  Updated Slack channel ID for: {p['name']}")
                else:
                    print(f"  Project exists: {p['name']}")
                project_objects.append(existing)
            else:
                new_project = Project(
                    name=p["name"],
                    description=f"AI-managed project: {p['name']}",
                    status=ProjectStatus.ACTIVE,
                    slack_channel_id=p["slack_channel_id"],
                    created_by=creator_user.id,
                )
                db.add(new_project)
                db.flush()
                print(f"  Created project: {p['name']} (id={new_project.id})")
                project_objects.append(new_project)

        # 3. Add all users as members with their Slack IDs
        for project in project_objects:
            for email, (user, slack_id) in user_objects.items():
                existing_member = db.query(ProjectMember).filter(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == user.id,
                ).first()
                if existing_member:
                    if not existing_member.slack_id:
                        existing_member.slack_id = slack_id
                    print(f"  Member exists: {email} in {project.name}")
                else:
                    member = ProjectMember(
                        project_id=project.id,
                        user_id=user.id,
                        slack_id=slack_id,
                    )
                    db.add(member)
                    print(f"  Added: {email} → {project.name} (slack={slack_id})")

        db.commit()
        print("\n✅ Seed complete!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print(f"🌱 Seeding: {DATABASE_URL}\n")
    seed()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Assume sqlite database for now or import from the backend module directly
import sys
import os
sys.path.append("/Users/rudraksh/AI_PM")

from src.backend.app.db.database import SessionLocal
from src.backend.app.model.user import User
from src.backend.app.model.project import Project, ProjectMember

with SessionLocal() as db:
    users = db.query(User).all()
    print("--- USERS ---")
    for u in users:
        print(f"User: {u.email} (ID: {u.id})")
        
    projects = db.query(Project).all()
    print("\n--- PROJECTS ---")
    for p in projects:
        print(f"Project: {p.name} (Created by: {p.created_by} | ID: {p.id})")
        
    members = db.query(ProjectMember).all()
    print("\n--- MEMBERSHIPS ---")
    for m in members:
        print(f"Project ID: {m.project_id} | User ID: {m.user_id}")

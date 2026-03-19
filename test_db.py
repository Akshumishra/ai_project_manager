import sys
sys.path.append("/Users/akshitamishra/Desktop/demo_1/ai-project-manager")
from src.backend.db.database import get_db, SessionLocal
from src.backend.model.user import User
import uuid

try:
    db = SessionLocal()
    users = db.query(User).all()
    print(f"Total Users in DB: {len(users)}")
    for u in users:
        print(f" - User: {u.id} | Email: {u.email} | Name: {u.name}")
except Exception as e:
    print(f"Error querying db: {e}")

import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from sqlalchemy import text
from src.backend.db.database import engine

def list_data():
    try:
        with engine.connect() as conn:
            print("--- Users ---")
            result = conn.execute(text("SELECT id, name, email FROM users"))
            for row in result:
                print(row)
            
            print("\n--- Projects ---")
            result = conn.execute(text("SELECT id, name FROM projects"))
            for row in result:
                print(row)
                
            print("\n--- Project Members ---")
            result = conn.execute(text("SELECT project_id, user_id, slack_id FROM project_members"))
            for row in result:
                print(row)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_data()

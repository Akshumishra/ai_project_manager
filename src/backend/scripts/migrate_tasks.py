import sys
import os
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.backend.db.database import engine
from src.backend.config import Config
from sqlalchemy import create_engine

def get_engines():
    engines = [engine]
    # Add postgres superuser engine
    postgres_url = "postgresql+psycopg2://postgres:password123@localhost:5432/ai_manager_db"
    engines.append(create_engine(postgres_url))
    return engines

def migrate():
    # Columns to add and rename
    queries = [
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS description VARCHAR;",
        "ALTER TABLE tasks RENAME COLUMN project_member_id TO assignee_id;"
    ]

    engines = get_engines()
    
    # We specifically want to use the superuser engine (index 1) if index 0 fails
    for idx, eng in enumerate(engines):
        print(f"Attempting migration with engine {idx}...")
        success = True
        with eng.connect() as conn:
            for query in queries:
                print(f"Executing: {query}")
                try:
                    conn.execute(text(query))
                    conn.commit()
                except Exception as e:
                    print(f"Error executing {query}: {e}")
                    conn.rollback()
                    if "already exists" in str(e) or "does not exist" in str(e):
                        # Skip if already renamed or added
                        continue
                    success = False
                    break 
        if success:
            print("Migration successful with this engine!")
            return
        else:
            print("Engine failed, trying next...")

    print("All migration attempts failed.")

def check_owner():
    query = "SELECT tableowner FROM pg_tables WHERE tablename = 'tasks';"
    with engine.connect() as conn:
        result = conn.execute(text(query))
        row = result.fetchone()
        if row:
            print(f"The 'tasks' table is owned by: {row[0]}")
        else:
            print("Could not find owner for 'tasks' table.")

if __name__ == "__main__":
    check_owner()
    migrate() 

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from sqlalchemy import create_engine, text

def clear_data():
    """Clear only standup-related tables and task logs, keeping tasks intact."""
    database_url = Config.DATABASE_URL or "sqlite:///./app.db"
    
    # Handle PostgreSQL URL replacement if needed
    if database_url and "app_user:test123" in database_url:
        print("💡 Detected app_user. Switching to postgres (owner) to bypass RLS for clearing...")
        database_url = database_url.replace("app_user:test123", "postgres:password123")
    
    engine = create_engine(database_url)
    
    tables = [
        "standup_action_logs",
        "standup_updates",
        "standups",
        "task_logs"
    ]
    
    print("🧹 Clearing data from standup and task log tables (keeping tasks)...")
    
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
    
    print("✅ All specified tables have been cleared. Tasks table is preserved!")

if __name__ == "__main__":
    clear_data()

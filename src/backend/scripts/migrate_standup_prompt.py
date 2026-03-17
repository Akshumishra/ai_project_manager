import os
import sys
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config

def add_prompt_column():
    # Use owner URL
    db_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    print(f"Connecting to {db_url.split('@')[-1]}...")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE standups ADD COLUMN IF NOT EXISTS prompt TEXT;"))
    print("Column 'prompt' added successfully or already exists.")

if __name__ == "__main__":
    add_prompt_column()

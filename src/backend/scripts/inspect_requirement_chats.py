import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from sqlalchemy import text
from src.backend.db.database import engine

def diagnose():
    try:
        with engine.connect() as conn:
            print("\n--- requirement_chats Columns ---")
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'requirement_chats' AND table_schema = 'public'
            """))
            for row in result:
                print(row)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diagnose()

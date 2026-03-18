import sys
import os
from sqlalchemy import desc

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.backend.db.database_standup import SessionStandup
from src.backend.model.standup import Standup

def inspect_last_prompt():
    db = SessionStandup()
    try:
        last_standup = db.query(Standup).order_by(desc(Standup.created_at)).first()
        if not last_standup:
            print("No standup found.")
            return

        print(f"--- Last Standup Prompt (ID: {last_standup.id}) ---")
        print(last_standup.prompt)
        print("-----------------------------------------------")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_last_prompt()

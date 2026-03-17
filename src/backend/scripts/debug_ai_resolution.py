
import os
import sys
import json
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.backend.agents.standup_agent import StandupReplyAgent

def debug_parsing():
    print("🔍 Debugging AI Blocker Resolution Response...")
    agent = StandupReplyAgent()
    
    user_name = "Aarushi"
    reply_text = "@ai-pm-bot akshita has started her work so my blocker is resolved."
    
    # Simple active tasks for context
    active_tasks = [
        {"id": "task1", "name": "Setup Recruitment Pipeline", "status": "blocked"}
    ]
    
    result = agent.parse_reply(user_name, reply_text, active_tasks, team_members=["Aarushi", "Akshita"])
    
    print("\n--- AI Response ---")
    print(f"Updates: {result.updates}")
    print(f"Blockers: {result.blockers}")
    print(f"Resolved Blockers: {result.resolved_blockers}")
    print(f"Sentiment: {result.sentiment}")

if __name__ == "__main__":
    debug_parsing()

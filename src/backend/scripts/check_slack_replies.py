
import os
import sys
import requests
import json

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.backend.config import Config

def check_replies(thread_ts):
    token = Config.SLACK_BOT_TOKEN
    channel_id = "C0ALTNG8HQU"
    
    url = "https://slack.com/api/conversations.replies"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"channel": channel_id, "ts": thread_ts}
    
    print(f"🔍 Fetching replies for channel {channel_id}, thread {thread_ts}...")
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        result = response.json()
        
        if not result.get("ok"):
            print(f"❌ Slack API Error: {result.get('error')}")
            return

        messages = result.get("messages", [])
        print(f"Found {len(messages)} messages in thread (including prompt).")
        for i, r in enumerate(messages):
            print(f"[{i}] User: {r.get('user')} | Text: {r.get('text')[:50].replace('\n', ' ')}... | TS: {r.get('ts')}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Test latest (failing)
    check_replies("1773638438.563199")
    print("-" * 20)
    # Test previous (working)
    check_replies("1773631251.651059")

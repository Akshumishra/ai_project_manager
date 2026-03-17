
import os
import sys
import requests

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.backend.config import Config

def check_channel_history():
    token = Config.SLACK_BOT_TOKEN
    channel_id = "C0ALTNG8HQU" # recrude
    url = "https://slack.com/api/conversations.history"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"channel": channel_id, "limit": 20}
    
    print(f"🔍 Fetching history for channel {channel_id}...")
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            print(f"❌ Slack API Error: {result.get('error')}")
            return

        messages = result.get("messages", [])
        print(f"Found {len(messages)} messages in channel.")
        for i, m in enumerate(messages):
            user = m.get('user')
            text = m.get('text', '')[:100].replace('\n', ' ')
            ts = m.get('ts')
            thread_ts = m.get('thread_ts')
            print(f"[{i}] User: {user} | Text: {text} | TS: {ts} | Thread_TS: {thread_ts}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_channel_history()

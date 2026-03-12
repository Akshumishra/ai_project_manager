import requests
import json

def simulate_slack_event():
    url = "http://localhost:8000/slack/events"
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "user": "U0AL9DCL2L8",
            "text": "<@U0AJZR4M0DD> what is the status of the AI Project Manager project?",
            "channel": "C0AK49YQQJK",
            "ts": "1234567890.123456"
        }
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    simulate_slack_event()

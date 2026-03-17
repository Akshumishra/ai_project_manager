import sys
import os
import requests

# Add searching at project root
sys.path.append(os.getcwd())

def trigger_all():
    url = "http://localhost:8000/standup/trigger-all"
    print(f"🚀 Triggering all standups via {url}...")
    try:
        response = requests.post(url)
        if response.status_code == 200:
            print("✅ SUCCESS: Standups initiated across all project channels.")
            print(f"Results: {response.json()}")
        else:
            print(f"❌ FAILED: Server returned status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ ERROR: Could not connect to server: {e}")
        print("💡 Make sure the server is running (python3 src/backend/main.py)")

if __name__ == "__main__":
    trigger_all()


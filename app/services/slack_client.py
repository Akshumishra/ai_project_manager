import os
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

if not SLACK_BOT_TOKEN:
    raise RuntimeError("SLACK_BOT_TOKEN not found")

slack_client = WebClient(token=SLACK_BOT_TOKEN)
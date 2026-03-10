from fastapi import APIRouter, HTTPException
from slack_sdk.errors import SlackApiError
from app.services.slack_client import slack_client

router = APIRouter()

@router.post("/send-message")
def send_message(channel_id: str, message: str):

    try:
        response = slack_client.chat_postMessage(
            channel=channel_id,
            text=message
        )

        return {
            "status": "success",
            "channel": channel_id,
            "timestamp": response["ts"]
        }

    except SlackApiError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Slack API error: {e.response['error']}"
        )


@router.get("/thread-replies")
def get_thread_replies(channel_id: str, thread_ts: str):

    try:
        response = slack_client.conversations_replies(
            channel=channel_id,
            ts=thread_ts
        )

        messages = response["messages"]

        replies = []

        for msg in messages:
            replies.append({
                "user": msg.get("user"),
                "text": msg.get("text"),
                "timestamp": msg.get("ts")
            })

        return {
            "channel": channel_id,
            "thread_ts": thread_ts,
            "reply_count": len(replies),
            "replies": replies
        }

    except SlackApiError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Slack API error: {e.response['error']}"
        )
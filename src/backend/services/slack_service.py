import requests
import logging
from typing import Optional, Dict, Any, List
from src.backend.config import Config

logger = logging.getLogger(__name__)

class SlackService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or Config.SLACK_BOT_TOKEN
        self.base_url = "https://slack.com/api"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8"
        }

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        try:
            logger.debug(f"Making Slack API call to {endpoint} with data: {data}")
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Slack API response: {result}")
            
            if not result.get("ok"):
                error = result.get("error", "Unknown error")
                warning = result.get("warning", "")
                logger.error(f"Slack API error: {error}. Warning: {warning}")
                raise Exception(f"Slack API error: {error}. Warning: {warning}")
            
            logger.info(f"Slack API call successful: {endpoint}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request error: {e}")
            raise Exception(f"Failed to connect to Slack API: {e}")

    def post_message(self, channel: str, text: str, thread_ts: Optional[str] = None) -> str:
        """Posts a message to a Slack channel or thread. Returns the message timestamp."""
        if not self.token:
            error_msg = "SLACK_BOT_TOKEN is not set. Cannot post to Slack."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if not channel:
            error_msg = "Channel ID is required but was not provided."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if not text or not text.strip():
            error_msg = "Message text is empty. Cannot post empty message to Slack."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        payload = {
            "channel": channel,
            "text": text
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        logger.debug(f"Posting message to channel {channel}, thread_ts={thread_ts}, text_length={len(text)}")
        logger.debug(f"Payload: {payload}")
        
        result = self._post("chat.postMessage", payload)
        
        if not result.get("ok"):
            error = result.get("error", "Unknown error")
            warning = result.get("warning", "")
            error_msg = f"Slack API returned error: {error}"
            if warning:
                error_msg += f". Warning: {warning}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        message_ts = result.get("ts")
        channel_id = result.get("channel")
        
        if not message_ts:
            error_msg = "Slack API returned success but no message timestamp. Message may not have been posted."
            logger.error(error_msg)
            logger.error(f"Full Slack response: {result}")
            raise Exception(error_msg)
        
        logger.info(f"✅ Message posted successfully to Slack. Channel: {channel_id}, Thread TS: {thread_ts}, Message TS: {message_ts}")
        logger.info(f"Message preview: {text[:100]}...")
        return message_ts

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Fetches basic user info from Slack."""
        url = f"{self.base_url}/users.info"
        params = {"user": user_id}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                raise Exception(f"Slack API error: {result.get('error')}")
            return result.get("user", {})
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request error: {e}")
            raise Exception(f"Failed to connect to Slack API: {e}")

    def list_replies(self, channel: str, thread_ts: str) -> List[Dict[str, Any]]:
        """
        Fetches all replies in a thread. 
        Includes a robust fallback to conversations.history if conversations.replies 
        is inconsistent (common when messages are very recent).
        """
        url = f"{self.base_url}/conversations.replies"
        params = {"channel": channel, "ts": thread_ts}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                raise Exception(f"Slack API error in replies: {result.get('error')}")
            
            messages = result.get("messages", [])
            
            # Robustness Check:
            # If reply_count > 0 but messages list only has the parent, 
            # Slack API might be lagging. Fall back to history.
            parent = messages[0] if messages else {}
            if parent.get("reply_count", 0) > (len(messages) - 1):
                logger.warning(f"Slack replies API returned only {len(messages)-1} replies for thread {thread_ts}, but parent says {parent.get('reply_count')}. Falling back to history search.")
                history_replies = self._fetch_replies_via_history(channel, thread_ts)
                if len(history_replies) > len(messages):
                    return history_replies

            return messages
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request error in list_replies: {e}")
            # Try fallback anyway if possible
            return self._fetch_replies_via_history(channel, thread_ts)
        except Exception as e:
            logger.error(f"Error in list_replies: {e}")
            return self._fetch_replies_via_history(channel, thread_ts)

    def _fetch_replies_via_history(self, channel: str, thread_ts: str) -> List[Dict[str, Any]]:
        """Fallback method to find threaded messages by scanning channel history."""
        url = f"{self.base_url}/conversations.history"
        params = {"channel": channel, "limit": 100}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                logger.error(f"Fallback history search failed: {result.get('error')}")
                return []
            
            messages = result.get("messages", [])
            # Filter messages that belong to this thread
            # Note: We sort by TS ascending to match the standard replies API output
            threaded = [m for m in messages if m.get("thread_ts") == thread_ts or m.get("ts") == thread_ts]
            threaded.sort(key=lambda x: x.get("ts", ""))
            
            if threaded:
                logger.info(f"Fallback history search found {len(threaded)} threaded messages for {thread_ts}")
            return threaded
        except Exception as e:
            logger.error(f"Error in fallback history search: {e}")
            return []

import httpx
from src.backend.config import Config
from src.backend.constants import SlackConstants
from src.backend.logger import get_logger

logger = get_logger("slack_service")

async def send_message(channel_id: str, text: str, thread_ts: str = None):
    url = SlackConstants.POST_MESSAGE_URL
    token = Config.SLACK_BOT_TOKEN
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    payload = {
        "channel": channel_id,
        "text": text
    }
    
    if thread_ts:
        payload["thread_ts"] = thread_ts
        
    logger.debug(f"Sending Slack message to channel {channel_id}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=SlackConstants.API_TIMEOUT
            )
            response.raise_for_status()
            logger.debug("Slack message sent successfully")
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"Error response {exc.response.status_code} while sending message: {exc.response.text}")
        except Exception as exc:
            logger.error(f"Error sending message to Slack: {exc}")
        
    return None

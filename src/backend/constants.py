class DefaultConstants:
    MODEL = "gpt-4.1-nano"
    TEMPERATURE = 0.5

class SlackConstants:
    API_BASE_URL = "https://slack.com/api"
    POST_MESSAGE_URL = f"{API_BASE_URL}/chat.postMessage"
    API_TIMEOUT = 10
import redis
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

try:
    from src.backend.db.redis import redis_client
    print("Attempting to ping Redis via src.backend.db.redis.redis_client...")
    response = redis_client.ping()
    print(f"Redis Ping Response: {response}")
except Exception as e:
    print(f"FAILED to connect to Redis: {e}")

try:
    from langchain_openai import ChatOpenAI
    from src.backend.config import settings
    from src.backend.task_creator.constants import TaskCreatorConstants as TaskConstants
    
    print(f"Testing model validity: {TaskConstants.MODEL}")
    llm = ChatOpenAI(
        model=TaskConstants.MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    # Just try a very small prompt
    res = llm.invoke("Hi")
    print(f"Model response: {res.content}")
except Exception as e:
    print(f"FAILED model test: {e}")

from rq import Queue
from src.backend.db.redis import redis_client

def get_redis_connection():
    """
    Returns the centralized Redis connection instance.
    """
    return redis_client

def get_queue(name="default"):
    """
    Returns an RQ Queue instance.
    """
    conn = get_redis_connection()
    if conn:
        return Queue(name, connection=conn)
    return None

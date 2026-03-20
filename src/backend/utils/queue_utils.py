from rq import Queue
from src.backend.db.redis import redis_client

def get_queue(name="default"):
    """
    Returns an RQ Queue instance.
    """
    conn = redis_client
    if conn:
        return Queue(name, connection=conn)
    return None

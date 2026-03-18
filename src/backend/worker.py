import sys
import os

# Add the project root to sys.path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from rq import Worker, Queue
from src.backend.db.redis import redis_client


listen = ['default']


def run_worker():
    conn = redis_client
    if not conn:
        print("Error: Could not connect to Redis. Ensure redis-server is running.")
        return

    queues = [Queue(name, connection=conn) for name in listen]
    worker = Worker(queues, connection=conn)
    print(f"RQ Worker started. Listening on queues: {listen}")
    worker.work()


if __name__ == '__main__':
    run_worker()

import json
from sqlalchemy.orm import Session

from src.backend.db.redis import redis_client
from src.backend.db.database import SessionLocal
from src.backend.model.document import DocumentBlock


def flush_dirty_blocks():

    db: Session = SessionLocal()

    try:

        # edge case 2.4, 2.5: Get oldest dirty blocks (up to 50 at a time) using ZRANGE
        block_ids = redis_client.zrange("dirty_blocks", 0, 49)

        if not block_ids:
            return

        # block_ids are strings (UUIDs) from Redis, no need to convert to int

        # split into batches of 10 to avoid too large transactions
        batches = [block_ids[i : i + 10] for i in range(0, len(block_ids), 10)]

        for batch in batches:

            for block_id in batch:

                data = redis_client.get(f"block_update:{block_id}")

                if not data:
                    # payload expired or removed, pop it from queue
                    redis_client.zrem("dirty_blocks", str(block_id))
                    continue

                data = json.loads(data)

                import uuid

                try:
                    uuid_obj = uuid.UUID(str(block_id))
                except ValueError:
                    continue

                block = (
                    db.query(DocumentBlock).filter(DocumentBlock.id == uuid_obj).first()
                )

                if block:
                    block.content = data.get("content", block.content)
                    block.type = data.get("type", block.type)

            try:
                db.commit()
            except Exception as e:
                db.rollback()
                print("DB Commit error for batch:", e)
                # Continue with next batch so one bad block doesn't halt the whole queue
                continue

            # remove processed blocks from the sorted set
            if batch:
                redis_client.zrem("dirty_blocks", *[str(b) for b in batch])

    except Exception as e:
        db.rollback()
        print("Batch sync error:", e)

    finally:
        db.close()

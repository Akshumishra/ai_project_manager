import json
import uuid
import logging
from sqlalchemy.orm import Session

from src.backend.db.redis import redis_client
from src.backend.db.database import get_session_local
from src.backend.model.document import DocumentBlock

logger = logging.getLogger(__name__)

def flush_dirty_blocks():
    db: Session = get_session_local()()
    try:
        # 1. Process Pending Inserts
        # Use SMEMBERS to get IDs added via SADD in services.py
        insert_ids = redis_client.smembers("pending_inserts")
        for b_id in insert_ids:
            # b_id is a string from Redis
            data_json = redis_client.get(f"pending_insert:{b_id}")
            if not data_json:
                redis_client.srem("pending_inserts", b_id)
                continue
            
            data = json.loads(data_json)
            
            # Optimization: If it's already marked for deletion, skip insertion
            if redis_client.sismember("pending_deletes", b_id):
                redis_client.srem("pending_inserts", b_id)
                redis_client.srem("pending_deletes", b_id)
                redis_client.delete(f"pending_insert:{b_id}")
                continue

            # Actual DB Insert with collision resolution
            try:
                # DocumentBlock might already exist if fallback to DB occurred during insert_block
                existing = db.query(DocumentBlock).filter(DocumentBlock.id == b_id).first()
                if not existing:
                    new_key = data["position_key"]
                    MAX_COLLISION_RETRIES = 3
                    inserted = False
                    for attempt in range(MAX_COLLISION_RETRIES):
                        try:
                            block = DocumentBlock(
                                id=data["block_id"],
                                doc_id=data["doc_id"],
                                content=data["content"],
                                position_key=new_key,
                                type=data["type"]
                            )
                            db.add(block)
                            db.commit()
                            inserted = True
                            break
                        except Exception as e:
                            db.rollback()
                            if "uq_doc_position" in str(e).lower():
                                import random
                                new_key = str(float(new_key) + random.uniform(0.0001, 0.0099))
                            else:
                                raise e
                    
                    if not inserted:
                        # All collision retries exhausted — move to dead letter
                        # DO NOT remove pending_insert key so the block stays visible
                        logger.error(f"Permanent collision for {b_id} after {MAX_COLLISION_RETRIES} attempts")
                        redis_client.sadd("dead_letter_inserts", b_id)
                        redis_client.srem("pending_inserts", b_id)
                        continue
                
                # Success or already exists - remove from queue
                redis_client.srem("pending_inserts", b_id)
                redis_client.delete(f"pending_insert:{b_id}")
            except Exception as e:
                db.rollback()
                logger.error(f"Critical sync error for {b_id}: {e}")
                # Move to dead-letter queue instead of just deleting
                redis_client.sadd("dead_letter_inserts", b_id)
                redis_client.srem("pending_inserts", b_id)

        # 2. Process Pending Edits (Content updates)
        block_ids = redis_client.zrange("dirty_blocks", 0, 49)
        if block_ids:
            for block_id in block_ids:
                data_json = redis_client.get(f"block_update:{block_id}")
                if not data_json:
                    redis_client.zrem("dirty_blocks", block_id)
                    continue
                
                data = json.loads(data_json)
                block = db.query(DocumentBlock).filter(DocumentBlock.id == block_id).first()
                if block:
                    block.content = data.get("content", block.content)
                    new_type = data.get("type")
                    if new_type is not None:
                        block.type = new_type
            
            try:
                db.commit()
                redis_client.zrem("dirty_blocks", *block_ids)
            except Exception as e:
                db.rollback()
                logger.error(f"Edit sync error: {e}")

        # 3. Process Pending Deletes
        delete_ids = redis_client.smembers("pending_deletes")
        for b_id in delete_ids:
            try:
                block = db.query(DocumentBlock).filter(DocumentBlock.id == b_id).first()
                if block:
                    db.delete(block)
                    db.commit()
                redis_client.srem("pending_deletes", b_id)
            except Exception as e:
                db.rollback()
                logger.error(f"Delete error for {b_id}: {e}")

    except Exception as e:
        logger.error(f"Worker loop error: {e}")
    finally:
        db.close()
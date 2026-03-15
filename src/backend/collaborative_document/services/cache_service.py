import json
import time
import redis
from uuid import UUID
from src.backend.db.redis import redis_client

def get_cached_document(doc_id: UUID):
    redis_key = f"doc:{doc_id}"
    cached = redis_client.get(redis_key)
    if cached:
        doc_data = json.loads(cached)
        if "title" in doc_data:
            return doc_data
    return None

def set_cached_document(doc_id: UUID, doc_data: dict):
    redis_key = f"doc:{doc_id}"
    # Ensure numeric sorting before caching
    if "blocks" in doc_data:
        doc_data["blocks"].sort(key=lambda x: float(x["position_key"]))
    redis_client.set(redis_key, json.dumps(doc_data), ex=3000)

def update_block_in_cache(doc_id: UUID, block_update: dict):
    redis_key = f"doc:{doc_id}"
    cached = redis_client.get(redis_key)
    if not cached:
        return

    doc_data = json.loads(cached)
    found = False
    for b in doc_data["blocks"]:
        if b["block_id"] == block_update["block_id"]:
            b.update(block_update)
            found = True
            break
    
    if not found:
        doc_data["blocks"].append(block_update)
    
    doc_data["blocks"].sort(key=lambda x: float(x["position_key"]))
    redis_client.set(redis_key, json.dumps(doc_data))

def remove_block_from_cache(doc_id: UUID, block_id: str):
    redis_key = f"doc:{doc_id}"
    cached = redis_client.get(redis_key)
    if not cached:
        return
    
    doc_data = json.loads(cached)
    doc_data["blocks"] = [b for b in doc_data["blocks"] if b["block_id"] != block_id]
    redis_client.set(redis_key, json.dumps(doc_data))

def buffer_block_insert(block_id: str, doc_id: UUID, block_data: dict):
    redis_client.set(f"pending_insert:{block_id}", json.dumps({"doc_id": str(doc_id), **block_data}))
    redis_client.sadd("pending_inserts", block_id)

def buffer_block_update(block_id: str, content: str, block_type: str = None):
    data = {"content": content}
    if block_type:
        data["type"] = block_type
    redis_client.set(f"block_update:{block_id}", json.dumps(data))
    redis_client.zadd("dirty_blocks", {block_id: time.time()})

def buffer_block_delete(block_id: str):
    redis_client.sadd("pending_deletes", block_id)

def get_pending_insert_pos(block_id: str):
    cached = redis_client.get(f"pending_insert:{block_id}")
    if cached:
        return json.loads(cached).get("position_key")
    return None

def get_pending_insert_doc_id(block_id: str):
    cached = redis_client.get(f"pending_insert:{block_id}")
    if cached:
        return UUID(json.loads(cached)["doc_id"])
    return None

def clear_pending_insert(block_id: str):
    redis_client.srem("pending_inserts", block_id)
    redis_client.delete(f"pending_insert:{block_id}")

def sync_title_to_cache(doc_id: UUID, title: str):
    redis_key = f"doc:{doc_id}"
    cached = redis_client.get(redis_key)
    if not cached:
        return
    try:
        doc_data = json.loads(cached)
        doc_data["title"] = title
        redis_client.set(redis_key, json.dumps(doc_data), ex=3000)
    except Exception:
        redis_client.delete(redis_key)

def delete_doc_cache(doc_id: UUID):
    redis_client.delete(f"doc:{doc_id}")

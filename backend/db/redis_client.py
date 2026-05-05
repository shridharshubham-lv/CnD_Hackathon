import json
import redis


def get_client() -> redis.Redis:
    return redis.Redis(host="localhost", port=6379, decode_responses=True)


def set_session(session_id: str, data: dict, ttl: int = 3600):
    client = get_client()
    client.setex(session_id, ttl, json.dumps(data))


def get_session(session_id: str) -> dict | None:
    client = get_client()
    raw = client.get(session_id)
    if raw is None:
        return None
    return json.loads(raw)


def delete_session(session_id: str):
    client = get_client()
    client.delete(session_id)

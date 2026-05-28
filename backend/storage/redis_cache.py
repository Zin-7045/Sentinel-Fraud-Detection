import json
from typing import Optional, Any
import redis

from backend.config import REDIS_HOST, REDIS_PORT


class RedisCache:
    def __init__(self, host: str = REDIS_HOST, port: int = REDIS_PORT,
                 db: int = 0, decode_responses: bool = True):
        self.client = redis.Redis(
            host=host, port=port, db=db,
            decode_responses=decode_responses,
            socket_connect_timeout=2,
            retry_on_timeout=True,
        )

    def get(self, key: str, default: Any = None) -> Any:
        try:
            val = self.client.get(key)
            if val is None:
                return default
            return val
        except redis.RedisError:
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            return self.client.set(key, value, ex=ttl)
        except redis.RedisError:
            return False

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        try:
            return self.client.incr(key, amount)
        except redis.RedisError:
            return None

    def expire(self, key: str, ttl: int) -> bool:
        try:
            return self.client.expire(key, ttl)
        except redis.RedisError:
            return False

    def cache_prediction(self, txn_id: str, result: dict, ttl: int = 3600):
        self.set(f"pred:{txn_id}", json.dumps(result), ttl=ttl)

    def get_cached_prediction(self, txn_id: str) -> Optional[dict]:
        val = self.get(f"pred:{txn_id}")
        return json.loads(val) if val else None

    def update_metrics(self, metrics: dict):
        for k, v in metrics.items():
            self.set(f"metrics:{k}", v, ttl=3600)

    def get_metrics(self) -> dict:
        keys = self.client.keys("metrics:*")
        result = {}
        for k in keys:
            name = k.replace("metrics:", "")
            result[name] = self.get(k)
        return result

    def close(self):
        self.client.close()

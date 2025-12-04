# managers/cache_manager.py
import redis
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self._check_connection()

    def _check_connection(self):
        try:
            self.client.ping()
            logger.info("[CACHE] Redis connecté OK")
        except redis.ConnectionError as e:
            logger.exception(f"[CACHE] Erreur connexion Redis: {e}")
            raise

    def set_user_data(self, user_id: str, data: dict, expire_sec: int = 3600 * 24):  # 24h TTL
        """Cache user data (ex. : current_user, token)."""
        key = f"user:{user_id}"
        self.client.set(key, json.dumps(data), ex=expire_sec)

    def get_user_data(self, user_id: str) -> Optional[dict]:
        key = f"user:{user_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None

    def cache_list(self, list_type: str, user_id: str, data: list, expire_sec: int = 300):  # 5min TTL pour fraîcheur
        """Cache lists (ex. : appointments, patients)."""
        key = f"list:{list_type}:{user_id}"
        self.client.set(key, json.dumps(data), ex=expire_sec)

    def get_cached_list(self, list_type: str, user_id: str) -> Optional[list]:
        key = f"list:{list_type}:{user_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None

    def clear_user_cache(self, user_id: str):
        """Clear sur logout/switch."""
        self.client.delete(f"user:{user_id}")
        self.client.delete(*self.client.keys(f"list:*:{user_id}"))
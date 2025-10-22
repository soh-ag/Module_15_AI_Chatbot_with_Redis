import redis
import json
import logging
from typing import Optional, Any
from .config import settings

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis_client = None
        self._connect()

    def _connect(self):
        """Establish connection to Redis"""
        try:
            connection_params = {
                'host': settings.REDIS_HOST,
                'port': settings.REDIS_PORT,
                'db': settings.REDIS_DB,
                'decode_responses': True
            }
            if settings.REDIS_PASSWORD:
                connection_params['password'] = settings.REDIS_PASSWORD
                
            self.redis_client = redis.Redis(**connection_params)
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Successfully connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache"""
        if not self.redis_client:
            return None
            
        try:
            cached_value = self.redis_client.get(key)
            if cached_value:
                logger.info(f"✅ Cache hit for key: {key}")
                return json.loads(cached_value)
            logger.info(f"❌ Cache miss for key: {key}")
            return None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def set(self, key: str, value: Any, expiration: int = None) -> bool:
        """Store value in cache with expiration"""
        if not self.redis_client:
            return False
            
        try:
            if expiration is None:
                expiration = settings.CACHE_EXPIRATION
                
            serialized_value = json.dumps(value)
            result = self.redis_client.setex(key, expiration, serialized_value)
            logger.info(f"💾 Cached response for key: {key} (expires in {expiration}s)")
            return result
        except (redis.RedisError, TypeError) as e:
            logger.error(f"Error storing in cache: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
            
        try:
            result = self.redis_client.delete(key)
            logger.info(f"🗑️ Deleted cache key: {key}")
            return result > 0
        except redis.RedisError as e:
            logger.error(f"Error deleting from cache: {e}")
            return False

    def health_check(self) -> bool:
        """Check if Redis is healthy"""
        if not self.redis_client:
            return False
        try:
            return self.redis_client.ping()
        except redis.RedisError:
            return False

# Global cache instance
cache = RedisCache()
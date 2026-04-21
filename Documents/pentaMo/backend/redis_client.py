import redis
import json
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_url = settings.redis_url
        self.client = None
        self.connect()

    def connect(self):
        try:
            if self.redis_url:
                self.client = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                self.client.ping()
                logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    def get(self, key):
        if not self.client:
            return None
        return self.client.get(key)

    def set(self, key, value, ex=None):
        if not self.client:
            return None
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return self.client.set(key, value, ex=ex)

    def is_connected(self):
        if not self.client:
            return False
        try:
            return self.client.ping()
        except:
            return False

redis_client = RedisClient()

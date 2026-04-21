"""
Security & Rate Limiting Service
Uses Redis to implement a sliding window rate limiter
"""

import time
import logging
from typing import Optional, Tuple
from backend.redis_client import redis_client

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Redis-based sliding window rate limiter
    """
    
    def __init__(self, key_prefix: str, limit: int, window_seconds: int):
        """
        Args:
            key_prefix: Prefix for Redis keys (e.g. "llm_limit", "feedback_limit")
            limit: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.key_prefix = key_prefix
        self.limit = limit
        self.window_seconds = window_seconds
        self.redis = redis_client
        
    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for the given identifier
        
        Returns:
            (is_allowed, remaining_hits)
        """
        if not self.redis.is_connected():
            # If Redis is down, we allow by default but log a warning
            logger.warning(f"Redis is down, bypass rate limit for {self.key_prefix}:{identifier}")
            return True, self.limit
            
        key = f"ratelimit:{self.key_prefix}:{identifier}"
        now = time.time()
        
        try:
            pipeline = self.redis.client.pipeline()
            # Remove timestamps outside the window
            pipeline.zremrangebyscore(key, 0, now - self.window_seconds)
            # Add current timestamp
            pipeline.zadd(key, {str(now): now})
            # Count elements in the window
            pipeline.zcard(key)
            # Set expiry for the key
            pipeline.expire(key, self.window_seconds)
            
            # Execute pipeline
            _, _, count, _ = pipeline.execute()
            
            is_allowed = count <= self.limit
            remaining = max(0, self.limit - count)
            
            if not is_allowed:
                logger.warning(f"Rate limit exceeded for {self.key_prefix}:{identifier} ({count}/{self.limit})")
                
            return is_allowed, remaining
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True, self.limit # Fail open if error in redis interaction

# Instance definitions
llm_rate_limiter = RateLimiter("llm", limit=10, window_seconds=60)      # 10 calls/min
feedback_rate_limiter = RateLimiter("feedback", limit=20, window_seconds=60) # 20 calls/min
tool_rate_limiter = RateLimiter("tool", limit=5, window_seconds=60)      # 5 calls/min

def check_llm_rate_limit(user_id: str) -> Tuple[bool, int]:
    """Check if user is allowed to call LLM"""
    return llm_rate_limiter.is_allowed(user_id)

def check_feedback_rate_limit(user_id: str) -> Tuple[bool, int]:
    """Check if user is allowed to send feedback"""
    return feedback_rate_limiter.is_allowed(user_id)

def check_tool_rate_limit(user_id: str) -> Tuple[bool, int]:
    """Check if agent is allowed to call tools"""
    return tool_rate_limiter.is_allowed(user_id)

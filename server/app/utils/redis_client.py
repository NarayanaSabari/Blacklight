"""Redis client utilities and caching helpers."""

import json
import redis
from typing import Any, Optional, Callable
from functools import wraps
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with utility methods."""
    
    def __init__(self, redis_connection: redis.Redis):
        """Initialize Redis client.
        
        Args:
            redis_connection: Redis connection instance
        """
        self.client = redis_connection
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        
        Returns:
            True if successful
        """
        try:
            self.client.set(key, json.dumps(value), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if successful
        """
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if exists
        """
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking cache existence: {e}")
            return False
    
    def clear(self, pattern: str = "*") -> int:
        """Clear cache by pattern.
        
        Args:
            pattern: Key pattern to match
        
        Returns:
            Number of keys deleted
        """
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter.
        
        Args:
            key: Counter key
            amount: Amount to increment
        
        Returns:
            New counter value
        """
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
            return 0
    
    def decr(self, key: str, amount: int = 1) -> int:
        """Decrement counter.
        
        Args:
            key: Counter key
            amount: Amount to decrement
        
        Returns:
            New counter value
        """
        try:
            return self.client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Error decrementing counter: {e}")
            return 0
    
    def rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check rate limit.
        
        Args:
            key: Rate limit key
            limit: Maximum requests
            window: Time window in seconds
        
        Returns:
            True if within limit
        """
        try:
            current = self.client.get(key)
            if current is None:
                self.client.setex(key, window, 1)
                return True
            
            current_int = int(current)
            if current_int < limit:
                self.client.incr(key)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        Generated cache key
    """
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    return ":".join(key_parts)


def cached(ttl: int = 3600, key_prefix: str = "cache"):
    """Cache decorator for functions with cache stampede protection.
    
    Uses Redis SET NX (set if not exists) to prevent multiple concurrent
    requests from regenerating the same cache value (cache stampede).
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from app import redis_client
            
            if redis_client is None:
                return func(*args, **kwargs)
            
            # Generate cache key
            cache_id = cache_key(key_prefix, func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_value = redis_client.get(cache_id)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_id}")
                return cached_value
            
            # Cache miss - acquire lock to prevent stampede
            lock_key = f"{cache_id}:lock"
            lock_acquired = False
            
            try:
                # Try to acquire lock (10 second TTL, NX = only if doesn't exist)
                lock_acquired = redis_client.client.set(lock_key, "1", nx=True, ex=10)
                
                if lock_acquired:
                    # We got the lock - compute the value
                    logger.debug(f"Cache miss, lock acquired: {cache_id}")
                    result = func(*args, **kwargs)
                    
                    # Store in cache
                    redis_client.set(cache_id, result, ttl=ttl)
                    logger.debug(f"Cache set: {cache_id}")
                    
                    return result
                else:
                    # Another request is computing the value - wait and retry
                    logger.debug(f"Cache miss, waiting for lock: {cache_id}")
                    import time
                    for attempt in range(10):  # Wait up to ~5 seconds
                        time.sleep(0.5)
                        cached_value = redis_client.get(cache_id)
                        if cached_value is not None:
                            logger.debug(f"Cache hit after waiting: {cache_id}")
                            return cached_value
                    
                    # Timeout - compute value anyway
                    logger.warning(f"Cache lock timeout, computing anyway: {cache_id}")
                    return func(*args, **kwargs)
                    
            except Exception as e:
                logger.error(f"Cache stampede protection error: {e}")
                # Fallback to direct computation
                return func(*args, **kwargs)
            finally:
                # Release lock if we acquired it
                if lock_acquired:
                    try:
                        redis_client.client.delete(lock_key)
                    except Exception as e:
                        logger.error(f"Error releasing cache lock: {e}")
        
        return wrapper
    return decorator
"""
Redis Cache Service
Provides caching functionality for frequently accessed data
"""
import json
from typing import Optional, Any
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service"""
    
    # Cache key prefixes
    USER_PREFIX = "user:"
    SESSION_PREFIX = "session:"
    BOOKING_PREFIX = "booking:"
    DOG_PREFIX = "dog:"
    STATS_PREFIX = "stats:"
    LOCATION_PREFIX = "location:"
    
    # Default TTLs
    DEFAULT_TTL = timedelta(minutes=15)
    SESSION_TTL = timedelta(days=30)
    STATS_TTL = timedelta(minutes=5)
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: timedelta = None) -> bool:
        """Set value in cache with optional TTL"""
        try:
            ttl = ttl or self.DEFAULT_TTL
            await self.redis.setex(
                key,
                int(ttl.total_seconds()),
                json.dumps(value, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    # ==================== USER CACHE ====================
    
    async def get_user(self, user_id: str) -> Optional[dict]:
        """Get user from cache"""
        return await self.get(f"{self.USER_PREFIX}{user_id}")
    
    async def set_user(self, user_id: str, user_data: dict) -> bool:
        """Cache user data"""
        return await self.set(f"{self.USER_PREFIX}{user_id}", user_data)
    
    async def invalidate_user(self, user_id: str) -> bool:
        """Invalidate user cache"""
        return await self.delete(f"{self.USER_PREFIX}{user_id}")
    
    # ==================== SESSION CACHE ====================
    
    async def get_session(self, token: str) -> Optional[dict]:
        """Get session data from cache"""
        return await self.get(f"{self.SESSION_PREFIX}{token}")
    
    async def set_session(self, token: str, session_data: dict) -> bool:
        """Cache session data"""
        return await self.set(f"{self.SESSION_PREFIX}{token}", session_data, self.SESSION_TTL)
    
    async def invalidate_session(self, token: str) -> bool:
        """Invalidate session"""
        return await self.delete(f"{self.SESSION_PREFIX}{token}")
    
    # ==================== BOOKING CACHE ====================
    
    async def get_booking(self, booking_id: str) -> Optional[dict]:
        """Get booking from cache"""
        return await self.get(f"{self.BOOKING_PREFIX}{booking_id}")
    
    async def set_booking(self, booking_id: str, booking_data: dict) -> bool:
        """Cache booking data"""
        return await self.set(f"{self.BOOKING_PREFIX}{booking_id}", booking_data)
    
    async def invalidate_booking(self, booking_id: str) -> bool:
        """Invalidate booking cache"""
        return await self.delete(f"{self.BOOKING_PREFIX}{booking_id}")
    
    async def invalidate_all_bookings(self) -> int:
        """Invalidate all booking caches"""
        return await self.delete_pattern(f"{self.BOOKING_PREFIX}*")
    
    # ==================== DOG CACHE ====================
    
    async def get_dog(self, dog_id: str) -> Optional[dict]:
        """Get dog from cache"""
        return await self.get(f"{self.DOG_PREFIX}{dog_id}")
    
    async def set_dog(self, dog_id: str, dog_data: dict) -> bool:
        """Cache dog data"""
        return await self.set(f"{self.DOG_PREFIX}{dog_id}", dog_data)
    
    async def invalidate_dog(self, dog_id: str) -> bool:
        """Invalidate dog cache"""
        return await self.delete(f"{self.DOG_PREFIX}{dog_id}")
    
    # ==================== STATS CACHE ====================
    
    async def get_stats(self, stats_key: str) -> Optional[dict]:
        """Get cached stats"""
        return await self.get(f"{self.STATS_PREFIX}{stats_key}")
    
    async def set_stats(self, stats_key: str, stats_data: dict) -> bool:
        """Cache stats data"""
        return await self.set(f"{self.STATS_PREFIX}{stats_key}", stats_data, self.STATS_TTL)
    
    async def invalidate_stats(self) -> int:
        """Invalidate all stats caches"""
        return await self.delete_pattern(f"{self.STATS_PREFIX}*")
    
    # ==================== LOCATION CACHE ====================
    
    async def get_locations(self) -> Optional[list]:
        """Get cached locations"""
        return await self.get(f"{self.LOCATION_PREFIX}all")
    
    async def set_locations(self, locations: list) -> bool:
        """Cache locations data"""
        return await self.set(f"{self.LOCATION_PREFIX}all", locations, timedelta(hours=1))
    
    async def invalidate_locations(self) -> bool:
        """Invalidate locations cache"""
        return await self.delete(f"{self.LOCATION_PREFIX}all")

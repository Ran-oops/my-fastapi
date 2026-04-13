"""Async Cache Layer for Enterprise FastAPI.

This module provides:
- Redis connection pool configuration
- JSON serialization/deserialization
- Cache key generation strategies
- @cache and @invalidate_cache decorators for Service layer
- Support for Redis Sentinel cluster mode

Dependencies:
    - redis[asyncio] >= 5.0.0
    - aiocache >= 0.12.0
    - fastapi-cache2 >= 0.2.0 (optional, for request-level caching)

Usage:
    from app.core.cache import cache, invalidate_cache

    @cache(ttl=300, key_builder=lambda user_id: f"user:{user_id}")
    async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
        return await user_repo.get(session, id=user_id)

    @invalidate_cache(pattern="users:*")
    async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
        # ... update logic
"""

import functools
import hashlib
import inspect
import json
import pickle
import re
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, ParamSpec, TypeVar

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.asyncio.sentinel import Sentinel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Type variables for generic function signatures
P = ParamSpec("P")
T = TypeVar("T")


class CacheConfig:
    """Cache configuration settings."""

    # Redis connection settings
    REDIS_URL: str = getattr(settings, "REDIS_CACHE_URL", "redis://localhost:6379/1")
    REDIS_SENTINEL_HOSTS: list[tuple[str, int]] = getattr(
        settings,
        "REDIS_SENTINEL_HOSTS",
        [("localhost", 26379)],
    )
    REDIS_SENTINEL_MASTER_NAME: str = getattr(
        settings,
        "REDIS_SENTINEL_MASTER_NAME",
        "mymaster",
    )
    REDIS_PASSWORD: str | None = getattr(settings, "REDIS_PASSWORD", None)

    # Pool settings
    REDIS_POOL_MAX_CONNECTIONS: int = getattr(settings, "REDIS_POOL_MAX_CONNECTIONS", 100)
    REDIS_SOCKET_TIMEOUT: float = getattr(settings, "REDIS_SOCKET_TIMEOUT", 5.0)
    REDIS_SOCKET_CONNECT_TIMEOUT: float = getattr(
        settings,
        "REDIS_SOCKET_CONNECT_TIMEOUT",
        5.0,
    )

    # Serialization settings
    SERIALIZER: str = getattr(settings, "CACHE_SERIALIZER", "json")  # "json" or "pickle"
    DEFAULT_TTL: int = getattr(settings, "CACHE_DEFAULT_TTL", 300)  # 5 minutes

    # Sentinel mode
    USE_SENTINEL: bool = getattr(settings, "REDIS_USE_SENTINEL", False)


class CacheKeyBuilder:
    """Cache key generation strategies."""

    @staticmethod
    def simple_key_builder(
        func: Callable[..., Any],
        prefix: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Build a simple cache key from function name and arguments.

        Args:
            func: The cached function
            prefix: Optional prefix for the key
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        func_name = f"{func.__module__}.{func.__qualname__}"
        key_parts = [prefix] if prefix else []
        key_parts.append(func_name)

        # Serialize args and kwargs
        if args:
            key_parts.append(_serialize_args(args))
        if kwargs:
            key_parts.append(_serialize_kwargs(kwargs))

        return ":".join(key_parts)

    @staticmethod
    def hash_key_builder(
        func: Callable[..., Any],
        prefix: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Build a hash-based cache key for longer keys.

        Args:
            func: The cached function
            prefix: Optional prefix for the key
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Hashed cache key string
        """
        simple_key = CacheKeyBuilder.simple_key_builder(func, prefix, *args, **kwargs)
        hash_value = hashlib.md5(simple_key.encode()).hexdigest()[:16]
        func_short = func.__qualname__[:50]
        return f"{prefix}:{func_short}:{hash_value}" if prefix else f"{func_short}:{hash_value}"

    @staticmethod
    def custom_key_builder(key_template: str) -> Callable[..., str]:
        """Create a custom key builder from a template string.

        Args:
            key_template: Template string with {arg_name} placeholders

        Returns:
            Key builder function
        """

        def builder(func: Callable[..., Any], prefix: str | None = None, *args: Any, **kwargs: Any) -> str:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            try:
                key = key_template.format(**bound.arguments)
                return f"{prefix}:{key}" if prefix else key
            except (KeyError, ValueError) as e:
                logger.warning(
                    "Failed to build custom cache key",
                    error=str(e),
                    template=key_template,
                    function=func.__qualname__,
                )
                # Fallback to simple builder
                return CacheKeyBuilder.simple_key_builder(func, prefix, *args, **kwargs)

        return builder


def _serialize_args(args: tuple[Any, ...]) -> str:
    """Serialize positional arguments for cache key."""
    try:
        # Filter out session and other non-serializable objects
        serializable_args = [
            arg
            for arg in args
            if not hasattr(arg, "__class__") or arg.__class__.__name__ in ("int", "str", "float", "bool", "type(None)")
        ]
        return json.dumps(serializable_args, default=str, sort_keys=True)
    except (TypeError, ValueError):
        return str(hash(args))


def _serialize_kwargs(kwargs: dict[str, Any]) -> str:
    """Serialize keyword arguments for cache key."""
    try:
        # Filter out session and other non-serializable objects
        serializable_kwargs = {
            k: v
            for k, v in kwargs.items()
            if not hasattr(v, "__class__") or v.__class__.__name__ in ("int", "str", "float", "bool", "type(None)")
        }
        return json.dumps(serializable_kwargs, default=str, sort_keys=True)
    except (TypeError, ValueError):
        return str(hash(tuple(kwargs.items())))


class CacheSerializer:
    """Cache value serialization/deserialization."""

    @staticmethod
    def serialize(value: Any) -> bytes | str:
        """Serialize a value for caching.

        Args:
            value: Value to serialize

        Returns:
            Serialized bytes or string
        """
        if CacheConfig.SERIALIZER == "json":
            return json.dumps(value, default=_json_default_encoder, ensure_ascii=False)
        return pickle.dumps(value)

    @staticmethod
    def deserialize(data: bytes | str) -> Any:
        """Deserialize a cached value.

        Args:
            data: Serialized data

        Returns:
            Deserialized value
        """
        if CacheConfig.SERIALIZER == "json":
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return json.loads(data)
        if isinstance(data, str):
            data = data.encode("utf-8")
        return pickle.loads(data)


def _json_default_encoder(obj: Any) -> Any:
    """JSON encoder for complex types."""
    if hasattr(obj, "isoformat"):  # datetime/date objects
        return obj.isoformat()
    if hasattr(obj, "__dict__"):  # Pydantic models or dataclasses
        return obj.__dict__
    if hasattr(obj, "value"):  # Enum
        return obj.value
    return str(obj)


class RedisCacheManager:
    """Redis cache connection manager with connection pooling."""

    _instance: "RedisCacheManager | None" = None
    _redis: Redis | None = None
    _sentinel: Sentinel | None = None

    def __new__(cls) -> "RedisCacheManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        if self._redis is not None:
            return

        try:
            if CacheConfig.USE_SENTINEL:
                self._redis = await self._init_sentinel()
                logger.info("Redis Sentinel cache initialized")
            else:
                self._redis = await self._init_standalone()
                logger.info("Redis standalone cache initialized")
        except Exception as e:
            logger.error("Failed to initialize Redis cache", error=str(e))
            raise

    async def _init_standalone(self) -> Redis:
        """Initialize standalone Redis connection."""
        return aioredis.from_url(
            CacheConfig.REDIS_URL,
            password=CacheConfig.REDIS_PASSWORD,
            max_connections=CacheConfig.REDIS_POOL_MAX_CONNECTIONS,
            socket_timeout=CacheConfig.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=CacheConfig.REDIS_SOCKET_CONNECT_TIMEOUT,
            decode_responses=False,  # We'll handle decoding ourselves
        )

    async def _init_sentinel(self) -> Redis:
        """Initialize Redis Sentinel connection."""
        self._sentinel = Sentinel(
            CacheConfig.REDIS_SENTINEL_HOSTS,
            password=CacheConfig.REDIS_PASSWORD,
            socket_timeout=CacheConfig.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=CacheConfig.REDIS_SOCKET_CONNECT_TIMEOUT,
        )
        return self._sentinel.master_for(CacheConfig.REDIS_SENTINEL_MASTER_NAME)

    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis cache connection closed")

    @property
    def redis(self) -> Redis:
        """Get Redis client instance."""
        if self._redis is None:
            raise RuntimeError("Redis cache not initialized. Call initialize() first.")
        return self._redis

    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False


# Global cache manager instance
cache_manager = RedisCacheManager()


async def init_cache() -> None:
    """Initialize the cache system."""
    await cache_manager.initialize()


async def close_cache() -> None:
    """Close the cache system."""
    await cache_manager.close()


@asynccontextmanager
async def cache_context():
    """Context manager for cache operations."""
    try:
        await init_cache()
        yield cache_manager
    finally:
        await close_cache()


def cache(
    ttl: int | None = None,
    key_builder: Callable[..., str] | None = None,
    prefix: str | None = None,
    skip_args: list[int] | None = None,
    condition: Callable[..., bool] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Cache decorator for async functions.

    Args:
        ttl: Time-to-live in seconds (default: 300)
        key_builder: Custom key builder function (func, prefix, *args, **kwargs) -> str
        prefix: Key prefix (default: function module.name)
        skip_args: Indices of args to skip in key generation (e.g., [0] to skip session)
        condition: Function to check if result should be cached (result, *args, **kwargs) -> bool

    Returns:
        Decorated function

    Example:
        @cache(ttl=300, key_builder=lambda user_id: f"user:{user_id}")
        async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
            return await user_repo.get(session, id=user_id)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Skip caching if cache not initialized
            if cache_manager._redis is None:
                return await func(*args, **kwargs)

            # Build cache key
            cache_key = _build_cache_key(func, key_builder, prefix, skip_args, args, kwargs)

            # Try to get from cache
            try:
                cached_value = await cache_manager.redis.get(cache_key)
                if cached_value:
                    logger.debug("Cache hit", key=cache_key, function=func.__qualname__)
                    return CacheSerializer.deserialize(cached_value)  # type: ignore
            except Exception as e:
                logger.warning("Cache get error", error=str(e), key=cache_key)

            # Execute function
            result = await func(*args, **kwargs)

            # Check condition
            if condition and not condition(result, *args, **kwargs):
                return result  # type: ignore

            # Store in cache
            if result is not None:
                try:
                    serialized = CacheSerializer.serialize(result)
                    cache_ttl = ttl if ttl is not None else CacheConfig.DEFAULT_TTL
                    await cache_manager.redis.setex(cache_key, cache_ttl, serialized)
                    logger.debug(
                        "Cache set",
                        key=cache_key,
                        ttl=cache_ttl,
                        function=func.__qualname__,
                    )
                except Exception as e:
                    logger.warning("Cache set error", error=str(e), key=cache_key)

            return result  # type: ignore

        # Attach cache management methods
        wrapper.cache_key = lambda *a, **kw: _build_cache_key(  # type: ignore
            func, key_builder, prefix, skip_args, a, kw
        )
        wrapper.cache_delete = lambda *a, **kw: _delete_cache(  # type: ignore
            _build_cache_key(func, key_builder, prefix, skip_args, a, kw)
        )

        return wrapper  # type: ignore

    return decorator


def invalidate_cache(
    pattern: str | None = None,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Cache invalidation decorator for async functions.

    Args:
        pattern: Pattern to match keys for deletion (e.g., "users:*")
        key_builder: Custom key builder to generate specific key to delete

    Returns:
        Decorated function

    Example:
        @invalidate_cache(pattern="users:*")
        async def update_user(session: AsyncSession, user_id: int, data: UserUpdate) -> User:
            # ... update logic

        @invalidate_cache(key_builder=lambda user_id: f"user:{user_id}")
        async def delete_user(session: AsyncSession, user_id: int) -> None:
            # ... delete logic
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Execute function first
            result = await func(*args, **kwargs)

            # Skip if cache not initialized
            if cache_manager._redis is None:
                return result  # type: ignore

            # Invalidate cache
            try:
                if pattern:
                    # Delete by pattern using scan
                    await _delete_by_pattern(pattern)
                    logger.debug("Cache invalidated by pattern", pattern=pattern, function=func.__qualname__)
                elif key_builder:
                    # Delete specific key
                    cache_key = key_builder(*args, **kwargs)
                    await cache_manager.redis.delete(cache_key)
                    logger.debug("Cache invalidated", key=cache_key, function=func.__qualname__)
            except Exception as e:
                logger.warning("Cache invalidation error", error=str(e), pattern=pattern, function=func.__qualname__)

            return result  # type: ignore

        return wrapper  # type: ignore

    return decorator


def _build_cache_key(
    func: Callable[..., Any],
    key_builder: Callable[..., str] | None,
    prefix: str | None,
    skip_args: list[int] | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    """Build cache key for a function call."""
    # Skip specified args (e.g., database session)
    if skip_args:
        filtered_args = tuple(arg for i, arg in enumerate(args) if i not in skip_args)
    else:
        # Default: skip first arg (usually session)
        filtered_args = args[1:] if len(args) > 1 else ()

    # Use custom key builder if provided
    if key_builder:
        try:
            return key_builder(*args, **kwargs)
        except Exception:
            pass  # Fallback to default

    # Default key building
    return CacheKeyBuilder.simple_key_builder(func, prefix or func.__module__.split(".")[-2], *filtered_args, **kwargs)


async def _delete_cache(key: str) -> None:
    """Delete a specific cache key."""
    if cache_manager._redis:
        await cache_manager.redis.delete(key)


async def _delete_by_pattern(pattern: str) -> int:
    """Delete cache keys by pattern.

    Returns:
        Number of keys deleted
    """
    if not cache_manager._redis:
        return 0

    deleted = 0
    cursor = 0

    while True:
        cursor, keys = await cache_manager.redis.scan(cursor, match=pattern, count=100)
        if keys:
            deleted += await cache_manager.redis.delete(*keys)
        if cursor == 0:
            break

    return deleted


# Convenience functions for manual cache operations


async def get_cache(key: str) -> Any | None:
    """Get value from cache.

    Args:
        key: Cache key

    Returns:
        Cached value or None
    """
    if not cache_manager._redis:
        return None
    try:
        data = await cache_manager.redis.get(key)
        return CacheSerializer.deserialize(data) if data else None
    except Exception as e:
        logger.warning("Cache get error", error=str(e), key=key)
        return None


async def set_cache(key: str, value: Any, ttl: int | None = None) -> bool:
    """Set value in cache.

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time-to-live in seconds (default: 300)

    Returns:
        True if successful
    """
    if not cache_manager._redis:
        return False
    try:
        serialized = CacheSerializer.serialize(value)
        cache_ttl = ttl if ttl is not None else CacheConfig.DEFAULT_TTL
        await cache_manager.redis.setex(key, cache_ttl, serialized)
        return True
    except Exception as e:
        logger.warning("Cache set error", error=str(e), key=key)
        return False


async def delete_cache(key: str) -> bool:
    """Delete a cache key.

    Args:
        key: Cache key to delete

    Returns:
        True if key existed and was deleted
    """
    if not cache_manager._redis:
        return False
    try:
        result = await cache_manager.redis.delete(key)
        return result > 0
    except Exception as e:
        logger.warning("Cache delete error", error=str(e), key=key)
        return False


async def delete_cache_pattern(pattern: str) -> int:
    """Delete cache keys by pattern.

    Args:
        pattern: Pattern to match (e.g., "users:*")

    Returns:
        Number of keys deleted
    """
    return await _delete_by_pattern(pattern)


async def clear_cache() -> bool:
    """Clear all cache entries (use with caution).

    Returns:
        True if successful
    """
    if not cache_manager._redis:
        return False
    try:
        await cache_manager.redis.flushdb()
        logger.warning("Cache cleared")
        return True
    except Exception as e:
        logger.error("Cache clear error", error=str(e))
        return False


async def get_cache_info() -> dict[str, Any]:
    """Get cache statistics and info.

    Returns:
        Dictionary with cache information
    """
    if not cache_manager._redis:
        return {"status": "not_initialized"}

    try:
        info = await cache_manager.redis.info()
        return {
            "status": "connected",
            "redis_version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

"""Async Redis connection manager implementing ``IAsyncCacheClient``."""

from functools import lru_cache
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from core.config import Settings, get_settings
from domain.interfaces import IAsyncCacheClient


class RedisManager(IAsyncCacheClient):
    """Encapsulated async Redis client lifecycle manager."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the manager without eagerly connecting.

        Args:
            settings: Validated application settings instance.
        """
        self._settings: Settings = settings
        self._client: Redis | None = None

    @property
    def settings(self) -> Settings:
        """Return the bound application settings."""
        return self._settings

    @property
    def is_connected(self) -> bool:
        """Return whether the Redis client has been initialized."""
        return self._client is not None

    async def connect(self) -> Redis:
        """Create or return the active Redis client.

        Returns:
            Connected async ``Redis`` client.
        """
        if self._client is None:
            self._client = aioredis.from_url(
                self._settings.redis_url,
                decode_responses=True,
            )
        return self._client

    async def get(self, key: str) -> str | None:
        """Retrieve a string value by key.

        Args:
            key: Redis key.

        Returns:
            Stored value or ``None`` if absent.
        """
        client = await self.connect()
        value: Any = await client.get(key)
        return str(value) if value is not None else None

    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        """Store a string value with an expiration TTL.

        Args:
            key: Redis key.
            value: String payload to store.
            ttl_seconds: Time-to-live in seconds.
        """
        client = await self.connect()
        await client.set(key, value, ex=ttl_seconds)

    async def dispose(self) -> None:
        """Close the Redis connection and release resources."""
        if self._client is not None:
            await self._client.aclose()
        self._client = None


_redis_manager: RedisManager | None = None


def get_redis_manager() -> IAsyncCacheClient:
    """Return the process-wide cache client singleton.

    Returns:
        ``IAsyncCacheClient`` implementation backed by Redis.
    """
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager(get_settings())
    return _redis_manager


async def get_redis_client() -> Redis:
    """FastAPI-compatible dependency returning an async Redis client.

    Returns:
        Connected async ``Redis`` client.
    """
    manager = get_redis_manager()
    if isinstance(manager, RedisManager):
        return await manager.connect()
    raise RuntimeError("Redis manager implementation does not expose a raw client.")

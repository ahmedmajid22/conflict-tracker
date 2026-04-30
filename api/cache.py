"""
Redis caching layer using Upstash REST API.
Falls back gracefully if Redis is unavailable — the API still works,
just without caching.
"""
from __future__ import annotations
import json
from typing import Any

from loguru import logger

from api.config import get_settings

_redis_client = None


def _get_redis():
    """Lazy-initialise the Upstash Redis client (singleton)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    if not settings.upstash_redis_rest_url or not settings.upstash_redis_rest_token:
        logger.warning("Upstash Redis credentials not set — caching disabled")
        return None

    try:
        from upstash_redis import Redis
        _redis_client = Redis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token,
        )
        logger.debug("Upstash Redis client initialised")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis init failed: {e} — caching disabled")
        return None


def cache_get(key: str) -> Any | None:
    """
    Retrieves a value from cache.
    Returns the parsed JSON value, or None on miss/error.
    """
    redis = _get_redis()
    if redis is None:
        return None
    try:
        raw = redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug(f"Cache GET miss/error for '{key}': {e}")
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """
    Stores a value in cache as JSON with a TTL.
    Silently does nothing on error.
    """
    redis = _get_redis()
    if redis is None:
        return
    try:
        redis.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception as e:
        logger.debug(f"Cache SET error for '{key}': {e}")


def cache_delete(key: str) -> None:
    """Removes a key from cache."""
    redis = _get_redis()
    if redis is None:
        return
    try:
        redis.delete(key)
    except Exception as e:
        logger.debug(f"Cache DELETE error for '{key}': {e}")


def cache_flush_prefix(prefix: str) -> None:
    """
    Deletes all keys that start with the given prefix.
    Useful for invalidating a group of related cached responses.
    """
    redis = _get_redis()
    if redis is None:
        return
    try:
        keys = redis.keys(f"{prefix}*")
        if keys:
            redis.delete(*keys)
            logger.debug(f"Flushed {len(keys)} cache keys with prefix '{prefix}'")
    except Exception as e:
        logger.debug(f"Cache flush error for prefix '{prefix}': {e}")
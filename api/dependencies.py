"""
Shared FastAPI dependencies — injected into route handlers via Depends().
"""
from __future__ import annotations
from functools import lru_cache

from fastapi import HTTPException, Query
from supabase import create_client, Client

from api.config import get_settings


@lru_cache
def get_supabase() -> Client:
    """
    Returns a singleton Supabase client.
    Raises 503 if credentials are missing.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise HTTPException(
            status_code=503,
            detail="Database credentials not configured",
        )
    return create_client(settings.supabase_url, settings.supabase_key)


def pagination_params(
    limit:  int = Query(default=50, ge=1,  le=200, description="Number of results to return"),
    offset: int = Query(default=0,  ge=0,            description="Number of results to skip"),
) -> dict:
    """
    Common pagination parameters injected into routes that need them.
    Enforces the configured max page size.
    """
    settings = get_settings()
    limit = min(limit, settings.max_page_size)
    return {"limit": limit, "offset": offset}
from __future__ import annotations
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from loguru import logger

from api.cache import cache_get, cache_set
from api.config import get_settings
from api.dependencies import get_supabase
from api.middleware.rate_limit import limiter

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()

_startup_time = datetime.now(timezone.utc)


@router.get(
    "",
    summary="API health check",
    description=(
        "Returns the status of all system components: "
        "the API server, the database, the cache, and "
        "the time since the last pipeline run."
    ),
)
@limiter.limit("30/minute")
async def health_check(
    request:  Request,
    supabase=Depends(get_supabase),
):
    cache_key = "health:status"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    status = {
        "api":       "ok",
        "database":  "unknown",
        "cache":     "unknown",
        "pipeline":  "unknown",
        "uptime_seconds": int((datetime.now(timezone.utc) - _startup_time).total_seconds()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Check database
    try:
        t0 = time.perf_counter()
        result = supabase.table("events").select("id").limit(1).execute()
        db_ms = round((time.perf_counter() - t0) * 1000)
        status["database"] = f"ok ({db_ms}ms)"
    except Exception as e:
        logger.warning(f"Health check — DB failed: {e}")
        status["database"] = "error"

    # Check cache
    try:
        test_key = "health:ping"
        cache_set(test_key, "pong", ttl_seconds=10)
        val = cache_get(test_key)
        status["cache"] = "ok" if val == "pong" else "error"
    except Exception as e:
        logger.warning(f"Health check — cache failed: {e}")
        status["cache"] = "error"

    # Check last pipeline run
    try:
        pipeline_result = (
            supabase.table("pipeline_runs")
            .select("run_at, inserted, fetched, duration_ms")
            .order("run_at", desc=True)
            .limit(1)
            .execute()
        )
        if pipeline_result.data:
            last_run = pipeline_result.data[0]
            run_time = datetime.fromisoformat(last_run["run_at"].replace("Z", "+00:00"))
            minutes_ago = int((datetime.now(timezone.utc) - run_time).total_seconds() / 60)
            status["pipeline"] = {
                "last_run_minutes_ago": minutes_ago,
                "last_inserted":        last_run.get("inserted", 0),
                "last_fetched":         last_run.get("fetched", 0),
                "last_duration_ms":     last_run.get("duration_ms", 0),
                "status": "ok" if minutes_ago < 30 else "stale",
            }
        else:
            status["pipeline"] = "no runs recorded"
    except Exception as e:
        logger.warning(f"Health check — pipeline check failed: {e}")
        status["pipeline"] = "error"

    cache_set(cache_key, status, ttl_seconds=settings.cache_ttl_health)
    return status


@router.get(
    "/ping",
    summary="Simple liveness check",
    description="Returns 'pong'. Used by Render.com to keep the service alive.",
    include_in_schema=False,
)
async def ping():
    return {"status": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}
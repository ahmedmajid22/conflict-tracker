from __future__ import annotations
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from loguru import logger

from api.cache import cache_get, cache_set
from api.config import get_settings
from api.dependencies import get_supabase
from api.middleware.rate_limit import limiter

router = APIRouter(prefix="/analytics", tags=["Analytics"])
settings = get_settings()


@router.get(
    "/sentiment-trend",
    summary="Daily sentiment trend",
    description=(
        "Returns daily average sentiment scores for the last N days. "
        "Values range from -1 (most negative) to +1 (most positive). "
        "Used to draw the main trend line chart."
    ),
)
@limiter.limit("60/minute")
async def sentiment_trend(
    request: Request,
    supabase=Depends(get_supabase),
    days: int = Query(default=90, ge=7, le=365, description="Number of days of history"),
):
    cache_key = f"analytics:sentiment_trend:{days}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        result = (
            supabase.table("sentiment_daily")
            .select("*")
            .gte("date", cutoff)
            .order("date", desc=False)
            .execute()
        )
        data = result.data or []
        response = {"data": data, "days": days, "count": len(data)}
        cache_set(cache_key, response, ttl_seconds=settings.cache_ttl_analytics)
        return response

    except Exception as e:
        logger.error(f"Error fetching sentiment trend: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch sentiment trend")


@router.get(
    "/category-breakdown",
    summary="Event count by category",
    description="Returns event counts grouped by category for the last 30 days.",
)
@limiter.limit("60/minute")
async def category_breakdown(
    request: Request,
    supabase=Depends(get_supabase),
):
    cache_key = "analytics:category_breakdown"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        result = supabase.rpc("category_counts_last_30_days").execute()
        data = result.data or []
        response = {"data": data}
        cache_set(cache_key, response, ttl_seconds=settings.cache_ttl_analytics)
        return response

    except Exception as e:
        logger.error(f"Error fetching category breakdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch category breakdown")


@router.get(
    "/top-entities",
    summary="Most-mentioned entities",
    description="Returns the most frequently mentioned named entities over the last N days.",
)
@limiter.limit("60/minute")
async def top_entities(
    request: Request,
    supabase=Depends(get_supabase),
    days:  int = Query(default=30, ge=1,  le=365,  description="Days of history"),
    limit: int = Query(default=20, ge=1,  le=100,  description="Number of entities to return"),
    type_: str | None = Query(default=None, alias="type", description="Filter by entity type: PERSON, ORG, GPE, NORP, EVENT"),
):
    cache_key = f"analytics:top_entities:{days}:{limit}:{type_}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Join entities → events to filter by date
        query = (
            supabase.table("entities")
            .select("name, type, count, events!inner(published_at)")
            .gte("events.published_at", cutoff)
        )

        if type_:
            query = query.eq("type", type_)

        result = query.order("count", desc=True).limit(limit * 3).execute()
        raw = result.data or []

        # Aggregate counts per entity name
        agg: dict[str, dict] = {}
        for row in raw:
            key = f"{row['name']}:{row['type']}"
            if key not in agg:
                agg[key] = {"name": row["name"], "type": row["type"], "total_count": 0}
            agg[key]["total_count"] += row.get("count", 1)

        sorted_entities = sorted(agg.values(), key=lambda x: x["total_count"], reverse=True)[:limit]
        response = {"data": sorted_entities, "days": days}
        cache_set(cache_key, response, ttl_seconds=settings.cache_ttl_analytics)
        return response

    except Exception as e:
        logger.error(f"Error fetching top entities: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch top entities")


@router.get(
    "/volume",
    summary="Event volume over time",
    description=(
        "Returns the number of events per day over the last N days. "
        "Used to draw the event volume bar chart."
    ),
)
@limiter.limit("60/minute")
async def event_volume(
    request: Request,
    supabase=Depends(get_supabase),
    days: int = Query(default=30, ge=7, le=365, description="Days of history"),
):
    cache_key = f"analytics:volume:{days}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = (
            supabase.table("sentiment_daily")
            .select("date, event_count")
            .gte("date", cutoff[:10])
            .order("date", desc=False)
            .execute()
        )
        data = result.data or []
        response = {"data": data, "days": days}
        cache_set(cache_key, response, ttl_seconds=settings.cache_ttl_analytics)
        return response

    except Exception as e:
        logger.error(f"Error fetching event volume: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch event volume")


@router.get(
    "/kpi",
    summary="Key performance indicators",
    description=(
        "Returns a summary of key stats: total event count, "
        "today's event count, average sentiment (last 7 days), "
        "most active source, and most common category. "
        "Used to populate the dashboard KPI tiles."
    ),
)
@limiter.limit("60/minute")
async def kpi_summary(
    request: Request,
    supabase=Depends(get_supabase),
):
    cache_key = "analytics:kpi"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        from datetime import date
        today     = date.today().isoformat()
        week_ago  = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        # Total events
        total_result = supabase.table("events").select("id", count="exact").execute()
        total_count = total_result.count or 0

        # Today's events
        today_result = (
            supabase.table("events")
            .select("id", count="exact")
            .gte("published_at", today)
            .execute()
        )
        today_count = today_result.count or 0

        # Average sentiment last 7 days
        sent_result = (
            supabase.table("sentiment_daily")
            .select("avg_score")
            .gte("date", week_ago[:10])
            .execute()
        )
        sent_data = sent_result.data or []
        avg_sentiment = (
            round(sum(r["avg_score"] for r in sent_data if r["avg_score"]) / len(sent_data), 3)
            if sent_data else 0.0
        )

        # Most active source
        source_result = (
            supabase.table("events")
            .select("source")
            .gte("published_at", week_ago)
            .execute()
        )
        sources = [r["source"] for r in (source_result.data or []) if r.get("source")]
        top_source = max(set(sources), key=sources.count) if sources else "N/A"

        # Most common category (last 7 days)
        cat_result = (
            supabase.table("events")
            .select("category")
            .gte("published_at", week_ago)
            .not_.is_("category", "null")
            .execute()
        )
        cats = [r["category"] for r in (cat_result.data or []) if r.get("category")]
        top_category = max(set(cats), key=cats.count) if cats else "N/A"

        response = {
            "total_events":   total_count,
            "today_events":   today_count,
            "avg_sentiment_7d": avg_sentiment,
            "top_source":     top_source,
            "top_category":   top_category,
        }

        cache_set(cache_key, response, ttl_seconds=settings.cache_ttl_analytics)
        return response

    except Exception as e:
        logger.error(f"Error fetching KPIs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch KPI summary")
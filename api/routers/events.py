from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Query, Request
from loguru import logger

from api.cache import cache_get, cache_set
from api.config import get_settings
from api.dependencies import get_supabase, pagination_params
from api.middleware.rate_limit import limiter

router = APIRouter(prefix="/events", tags=["Events"])
settings = get_settings()


def _build_cache_key(*parts) -> str:
    """Builds a Redis cache key from parts, replacing unsafe chars."""
    return "events:" + ":".join(str(p) for p in parts).replace(" ", "_")


@router.get(
    "",
    summary="List events",
    description=(
        "Returns a paginated list of conflict events, newest first. "
        "Supports filtering by category, source, date range, and whether "
        "the event has geographic coordinates."
    ),
)
@limiter.limit("60/minute")
async def list_events(
    request: Request,
    pagination: dict = Depends(pagination_params),
    supabase=Depends(get_supabase),
    category:    str | None = Query(None, description="Filter by category: military, diplomatic, economic, social, humanitarian, other"),
    source:      str | None = Query(None, description="Filter by source: bbc, reuters, gdelt, newsapi, al_jazeera, etc."),
    from_date:   str | None = Query(None, description="ISO 8601 start date, e.g. 2024-01-01"),
    to_date:     str | None = Query(None, description="ISO 8601 end date, e.g. 2024-12-31"),
    geolocated:  bool | None = Query(None, description="If true, only return events with lat/lon"),
    search:      str | None = Query(None, description="Full-text search across title and description"),
):
    limit  = pagination["limit"]
    offset = pagination["offset"]

    cache_key = _build_cache_key(
        category, source, from_date, to_date, geolocated, search, limit, offset
    )
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        query = (
            supabase.table("events")
            .select("*, sentiment(score, label, model_name)")
            .order("published_at", desc=True)
        )

        if category:
            query = query.eq("category", category)
        if source:
            query = query.eq("source", source)
        if from_date:
            query = query.gte("published_at", from_date)
        if to_date:
            query = query.lte("published_at", to_date)
        if geolocated is True:
            query = query.not_.is_("lat", "null")
        if search:
            # Supabase full-text search using ilike for simplicity
            query = query.or_(
                f"title.ilike.%{search}%,description.ilike.%{search}%"
            )

        result = query.range(offset, offset + limit - 1).execute()
        data = result.data or []

        response = {
            "data":   data,
            "count":  len(data),
            "limit":  limit,
            "offset": offset,
        }

        cache_set(cache_key, response, ttl_seconds=settings.cache_ttl_events)
        return response

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch events")


@router.get(
    "/map",
    summary="Events for map display",
    description=(
        "Returns up to 500 geolocated events optimised for map rendering. "
        "Each item includes only the fields needed for a map marker. "
        "Heavily cached (5 minutes)."
    ),
)
@limiter.limit("60/minute")
async def map_events(
    request: Request,
    supabase=Depends(get_supabase),
    category: str | None = Query(None, description="Filter by category"),
    days:     int        = Query(default=30, ge=1, le=365, description="Show events from last N days"),
):
    cache_key = _build_cache_key("map", category, days)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        query = (
            supabase.table("events")
            .select("id, title, lat, lon, category, published_at, source, sentiment(label, score)")
            .not_.is_("lat", "null")
            .not_.is_("lon", "null")
            .order("published_at", desc=True)
            .limit(500)
        )

        if category:
            query = query.eq("category", category)

        # Filter by days using Supabase's gte with a calculated timestamp
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        query = query.gte("published_at", cutoff)

        result = query.execute()
        data = result.data or []

        response = {"data": data, "count": len(data)}
        cache_set(cache_key, response, ttl_seconds=settings.cache_ttl_map)
        return response

    except Exception as e:
        logger.error(f"Error fetching map events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch map data")


@router.get(
    "/{event_id}",
    summary="Get a single event",
    description="Returns full details for a single event including sentiment and named entities.",
)
@limiter.limit("60/minute")
async def get_event(
    request:  Request,
    event_id: str,
    supabase=Depends(get_supabase),
):
    cache_key = f"event:detail:{event_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        result = (
            supabase.table("events")
            .select("*, sentiment(score, label, model_name), entities(name, type, count)")
            .eq("id", event_id)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Event not found")

        cache_set(cache_key, result.data, ttl_seconds=settings.cache_ttl_events)
        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch event")
from __future__ import annotations
import time
from typing import Any
from loguru import logger
from pipeline.db.supabase_client import get_client


def get_existing_hashes() -> set[str]:
    """
    Fetch all existing raw_hash values from the DB.
    Used for deduplication before inserting.
    Returns an empty set on error (fail-open: we might insert
    duplicates, but the UNIQUE constraint will reject them safely).
    """
    try:
        client = get_client()
        # Fetch in pages to handle large tables
        hashes: set[str] = set()
        page = 0
        page_size = 1000
        while True:
            result = (
                client.table("events")
                .select("raw_hash")
                .range(page * page_size, (page + 1) * page_size - 1)
                .execute()
            )
            rows = result.data or []
            for row in rows:
                hashes.add(row["raw_hash"])
            if len(rows) < page_size:
                break
            page += 1
        logger.debug(f"Loaded {len(hashes)} existing hashes from DB")
        return hashes
    except Exception as e:
        logger.warning(f"Could not fetch existing hashes: {e}")
        return set()


def write_event(record: dict[str, Any]) -> str | None:
    """
    Inserts a single event record into the events table.
    Returns the new event UUID on success, None on failure.
    The UNIQUE constraint on raw_hash means duplicate inserts
    are silently ignored.
    """
    client = get_client()
    payload = {
        "source":        record.get("source"),
        "title":         record.get("title"),
        "description":   record.get("description"),
        "url":           record.get("url"),
        "published_at":  record.get("published_at"),
        "location_name": record.get("location_name"),
        "lat":           record.get("lat"),
        "lon":           record.get("lon"),
        "category":      record.get("category"),
        "raw_hash":      record["raw_hash"],
        "is_processed":  False,
    }
    try:
        result = (
            client.table("events")
            .insert(payload, returning="representation")
            .execute()
        )
        if result.data:
            event_id = result.data[0]["id"]
            return event_id
    except Exception as e:
        # Unique constraint violation = duplicate, skip silently
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return None
        logger.error(f"Error inserting event '{record.get('title', '')}': {e}")
    return None


def write_sentiment(event_id: str, sentiment: dict[str, Any]) -> None:
    """
    Inserts a sentiment record linked to an event.
    """
    if not event_id or not sentiment:
        return
    client = get_client()
    try:
        client.table("sentiment").insert({
            "event_id":  event_id,
            "score":     sentiment.get("score", 0.0),
            "label":     sentiment.get("label", "neutral"),
            "model_name": sentiment.get("model_name", "unknown"),
        }).execute()
    except Exception as e:
        logger.error(f"Error inserting sentiment for event {event_id}: {e}")


def write_entities(event_id: str, entities: list[dict[str, Any]]) -> None:
    """
    Bulk inserts named entities linked to an event.
    """
    if not event_id or not entities:
        return
    client = get_client()
    rows = [
        {
            "event_id": event_id,
            "name":     ent.get("name"),
            "type":     ent.get("type"),
            "count":    ent.get("count", 1),
        }
        for ent in entities
        if ent.get("name")
    ]
    if not rows:
        return
    try:
        client.table("entities").insert(rows).execute()
    except Exception as e:
        logger.error(f"Error inserting entities for event {event_id}: {e}")


def write_pipeline_run(
    fetched: int,
    inserted: int,
    errors: str | None,
    duration_ms: int,
) -> None:
    """
    Logs a pipeline run summary to the pipeline_runs table.
    """
    client = get_client()
    try:
        client.table("pipeline_runs").insert({
            "fetched":     fetched,
            "inserted":    inserted,
            "errors":      errors,
            "duration_ms": duration_ms,
        }).execute()
    except Exception as e:
        logger.warning(f"Could not write pipeline run log: {e}")


def write_batch(records: list[dict[str, Any]]) -> int:
    """
    Processes a list of enriched records:
    1. Inserts the event
    2. Inserts sentiment
    3. Inserts named entities
    Returns count of successfully inserted events.
    """
    inserted = 0
    for record in records:
        event_id = write_event(record)
        if event_id:
            sentiment = record.get("sentiment")
            if sentiment:
                write_sentiment(event_id, sentiment)

            entities = record.get("entities", [])
            if entities:
                write_entities(event_id, entities)

            inserted += 1
            logger.debug(f"Inserted: {record.get('title', '')[:60]}")

    return inserted


def rebuild_sentiment_daily() -> None:
    """
    Calls the Supabase RPC function to rebuild the
    sentiment_daily aggregation table.
    """
    client = get_client()
    try:
        client.rpc("rebuild_sentiment_daily").execute()
        logger.info("Rebuilt sentiment_daily aggregates")
    except Exception as e:
        logger.error(f"Error rebuilding sentiment_daily: {e}")
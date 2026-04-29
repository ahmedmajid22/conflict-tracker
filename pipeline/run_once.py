"""
run_once.py — Runs one full pipeline cycle and exits.
Called by GitHub Actions every 15 minutes.
Usage: python -m pipeline.run_once
"""
from __future__ import annotations
import time
import sys
from loguru import logger

from pipeline.config import LOG_LEVEL
from pipeline.fetchers.rss_fetcher       import fetch_all_rss
from pipeline.fetchers.newsapi_fetcher   import fetch_all_newsapi
from pipeline.fetchers.gdelt_fetcher     import fetch_gdelt_events
from pipeline.processors.cleaner        import clean
from pipeline.processors.deduplicator   import deduplicate
from pipeline.processors.geocoder       import enrich_with_geocoordinates
from pipeline.processors.categorizer    import enrich_with_categories
from pipeline.processors.sentiment      import enrich_with_sentiment
from pipeline.processors.ner            import enrich_with_entities
from pipeline.db.writer                 import write_batch, write_pipeline_run, rebuild_sentiment_daily


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        level=LOG_LEVEL,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )
    logger.add(
        "logs/pipeline.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )


def run() -> None:
    import os
    os.makedirs("logs", exist_ok=True)
    setup_logging()

    start_time = time.time()
    logger.info("=" * 50)
    logger.info("Pipeline started")

    errors: list[str] = []
    fetched = 0
    inserted = 0

    # ── Step 1: Fetch from all sources ──────────────────
    logger.info("Step 1/6: Fetching data from sources...")
    raw_records: list[dict] = []

    try:
        rss_records = fetch_all_rss()
        raw_records.extend(rss_records)
        logger.info(f"  RSS:     {len(rss_records)} articles")
    except Exception as e:
        msg = f"RSS fetch failed: {e}"
        logger.error(msg)
        errors.append(msg)

    try:
        news_records = fetch_all_newsapi()
        raw_records.extend(news_records)
        logger.info(f"  NewsAPI: {len(news_records)} articles")
    except Exception as e:
        msg = f"NewsAPI fetch failed: {e}"
        logger.error(msg)
        errors.append(msg)

    try:
        gdelt_records = fetch_gdelt_events()
        raw_records.extend(gdelt_records)
        logger.info(f"  GDELT:   {len(gdelt_records)} events")
    except Exception as e:
        msg = f"GDELT fetch failed: {e}"
        logger.error(msg)
        errors.append(msg)

    fetched = len(raw_records)
    logger.info(f"Total fetched: {fetched}")

    if not raw_records:
        logger.warning("No records fetched — pipeline exiting early")
        write_pipeline_run(fetched=0, inserted=0, errors="No records fetched", duration_ms=0)
        return

    # ── Step 2: Clean ────────────────────────────────────
    logger.info("Step 2/6: Cleaning records...")
    records = clean(raw_records)

    # ── Step 3: Deduplicate ──────────────────────────────
    logger.info("Step 3/6: Deduplicating...")
    records = deduplicate(records)

    if not records:
        logger.info("No new records after deduplication — nothing to insert")
        elapsed = int((time.time() - start_time) * 1000)
        write_pipeline_run(fetched=fetched, inserted=0, errors=None, duration_ms=elapsed)
        return

    # ── Step 4: Enrich with geocoordinates ───────────────
    logger.info(f"Step 4/6: Geocoding {len(records)} records...")
    records = enrich_with_geocoordinates(records)

    # ── Step 5: Categorize + NER + Sentiment ─────────────
    logger.info("Step 5/6: Running NLP pipeline...")
    records = enrich_with_categories(records)
    records = enrich_with_entities(records)
    records = enrich_with_sentiment(records)

    # ── Step 6: Write to database ────────────────────────
    logger.info(f"Step 6/6: Writing {len(records)} records to database...")
    inserted = write_batch(records)

    # Rebuild daily aggregates
    try:
        rebuild_sentiment_daily()
    except Exception as e:
        logger.warning(f"Could not rebuild sentiment_daily: {e}")

    elapsed = int((time.time() - start_time) * 1000)
    write_pipeline_run(
        fetched=fetched,
        inserted=inserted,
        errors="; ".join(errors) if errors else None,
        duration_ms=elapsed,
    )

    logger.info("=" * 50)
    logger.info(f"Pipeline complete: {inserted} new records inserted in {elapsed}ms")


if __name__ == "__main__":
    run()
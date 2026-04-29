from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
from loguru import logger

from pipeline.config import RSS_FEEDS, CONFLICT_KEYWORDS


def _parse_date(date_str: str | None) -> str:
    """
    Parse various RSS date formats into ISO 8601 UTC string.
    Falls back to current UTC time if parsing fails.
    """
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    try:
        # Some feeds use strftime formats
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.astimezone(timezone.utc).isoformat()
            except ValueError:
                continue
    except Exception:
        pass
    return datetime.now(timezone.utc).isoformat()


def _is_relevant(title: str, description: str) -> bool:
    """
    Returns True if the article contains at least one conflict keyword.
    Case-insensitive check across title + description.
    """
    combined = (title + " " + description).lower()
    return any(keyword in combined for keyword in CONFLICT_KEYWORDS)


def _make_hash(title: str, url: str) -> str:
    """
    SHA-256 hash of title+url for deduplication.
    """
    raw = (title.strip() + url.strip()).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def fetch_rss(url: str, source_name: str) -> list[dict]:
    """
    Fetches and parses a single RSS feed.
    Returns a list of article dicts.
    """
    try:
        feed = feedparser.parse(url)
        if feed.bozo and feed.bozo_exception:
            logger.warning(
                f"[{source_name}] Feed parse warning: {feed.bozo_exception}"
            )

        records = []
        for entry in feed.entries:
            title       = entry.get("title", "").strip()
            description = entry.get("summary", entry.get("description", "")).strip()
            url_        = entry.get("link", "").strip()
            date_str    = entry.get("published", entry.get("updated", None))

            if not title or not url_:
                continue

            if not _is_relevant(title, description):
                continue

            records.append({
                "source":       source_name,
                "title":        title,
                "description":  description[:2000],  # cap length
                "url":          url_,
                "published_at": _parse_date(date_str),
                "raw_hash":     _make_hash(title, url_),
                # These are filled in later by processors
                "location_name": None,
                "lat":           None,
                "lon":           None,
                "category":      None,
                "sentiment":     None,
                "entities":      [],
            })

        logger.info(f"[{source_name}] Fetched {len(records)} relevant articles")
        return records

    except Exception as e:
        logger.error(f"[{source_name}] RSS fetch failed: {e}")
        return []


def fetch_all_rss() -> list[dict]:
    """
    Fetches all configured RSS feeds concurrently.
    Returns combined list of article dicts.
    """
    all_records: list[dict] = []
    for source_name, url in RSS_FEEDS:
        records = fetch_rss(url, source_name)
        all_records.extend(records)
    logger.info(f"RSS total: {len(all_records)} relevant articles from {len(RSS_FEEDS)} feeds")
    return all_records
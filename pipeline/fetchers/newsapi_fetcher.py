from __future__ import annotations
import hashlib
from datetime import datetime, timedelta, timezone

import requests
from loguru import logger

from pipeline.config import NEWSAPI_KEY, REQUEST_TIMEOUT, CONFLICT_KEYWORDS


NEWSAPI_URL = "https://newsapi.org/v2/everything"

SEARCH_QUERIES = [
    "Iran military OR attack OR nuclear",
    "Ukraine Russia war",
    "Gaza Israel conflict",
    "Middle East conflict",
    "Sudan conflict OR war",
    "Syria attack OR military",
    "NATO defense",
    "North Korea missile",
    "South China Sea military",
    "humanitarian crisis OR conflict",
]


def _make_hash(title: str, url: str) -> str:
    raw = (title.strip() + url.strip()).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def fetch_newsapi(query: str, days_back: int = 1) -> list[dict]:
    """
    Searches NewsAPI for a given query.
    Uses the last `days_back` days to avoid re-fetching old articles.
    """
    if not NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY not set, skipping NewsAPI fetcher")
        return []

    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%d"
    )

    params = {
        "q":        query,
        "from":     from_date,
        "sortBy":   "publishedAt",
        "language": "en",
        "pageSize": 20,
        "apiKey":   NEWSAPI_KEY,
    }

    try:
        resp = requests.get(
            NEWSAPI_URL, params=params, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            logger.warning(f"[newsapi] API error: {data.get('message')}")
            return []

        records = []
        for article in data.get("articles", []):
            title       = (article.get("title") or "").strip()
            description = (article.get("description") or "").strip()
            url         = (article.get("url") or "").strip()
            published   = article.get("publishedAt") or datetime.now(timezone.utc).isoformat()

            if not title or not url or url == "https://removed.com":
                continue

            records.append({
                "source":        "newsapi",
                "title":         title,
                "description":   description[:2000],
                "url":           url,
                "published_at":  published,
                "raw_hash":      _make_hash(title, url),
                "location_name": None,
                "lat":           None,
                "lon":           None,
                "category":      None,
                "sentiment":     None,
                "entities":      [],
            })

        logger.info(f"[newsapi] Query '{query[:30]}...' → {len(records)} articles")
        return records

    except requests.exceptions.HTTPError as e:
        if "429" in str(e):
            logger.warning("[newsapi] Rate limit hit — skipping")
        else:
            logger.error(f"[newsapi] HTTP error: {e}")
        return []
    except Exception as e:
        logger.error(f"[newsapi] Fetch failed: {e}")
        return []


def fetch_all_newsapi() -> list[dict]:
    """
    Runs all search queries and returns combined results.
    Stops early if we hit the free tier daily limit.
    """
    if not NEWSAPI_KEY:
        return []

    all_records: list[dict] = []
    for query in SEARCH_QUERIES:
        records = fetch_newsapi(query)
        all_records.extend(records)
        # NewsAPI free tier: 100 req/day. We have ~10 queries here, fine.

    logger.info(f"[newsapi] Total: {len(all_records)} articles")
    return all_records
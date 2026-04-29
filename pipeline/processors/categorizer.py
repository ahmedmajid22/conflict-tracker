from __future__ import annotations
from loguru import logger
from pipeline.config import CATEGORY_KEYWORDS


def categorize(text: str) -> str:
    """
    Assigns a category to an article based on keyword matching.
    The category with the most keyword hits wins.
    Falls back to 'other' if no keywords match.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score

    if not scores:
        return "other"

    return max(scores, key=lambda c: scores[c])


def enrich_with_categories(records: list[dict]) -> list[dict]:
    """
    Assigns a category to every record that doesn't already have one.
    """
    categorized = 0
    for record in records:
        if record.get("category"):
            continue  # Already has a category (e.g. from GDELT)

        text = f"{record.get('title', '')} {record.get('description', '')}"
        record["category"] = categorize(text)
        categorized += 1

    logger.info(f"Categorizer assigned categories to {categorized} records")
    return records
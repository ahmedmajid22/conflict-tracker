from __future__ import annotations
import re
import html
from loguru import logger


# Patterns to strip from text
_HTML_TAG_RE    = re.compile(r"<[^>]+>")
_WHITESPACE_RE  = re.compile(r"\s+")
_ENTITY_RE      = re.compile(r"&[a-zA-Z]+;|&#[0-9]+;")


def strip_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    if not text:
        return ""
    text = html.unescape(text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = _ENTITY_RE.sub(" ", text)
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into single spaces."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def clean_text(text: str) -> str:
    """Full text cleaning pipeline."""
    if not text:
        return ""
    text = strip_html(text)
    text = normalize_whitespace(text)
    return text


def clean_record(record: dict) -> dict:
    """
    Cleans a single record in-place.
    Modifies title and description fields.
    Returns the cleaned record.
    """
    record["title"]       = clean_text(record.get("title", ""))
    record["description"] = clean_text(record.get("description", ""))

    # Remove records with empty titles after cleaning
    # (these are effectively useless)
    return record


def clean(records: list[dict]) -> list[dict]:
    """
    Cleans a list of records.
    Drops records with empty titles.
    Returns only valid, cleaned records.
    """
    cleaned = []
    dropped = 0
    for record in records:
        cleaned_record = clean_record(record)
        if not cleaned_record.get("title"):
            dropped += 1
            continue
        cleaned.append(cleaned_record)

    if dropped:
        logger.debug(f"Cleaner dropped {dropped} records with empty titles")

    return cleaned
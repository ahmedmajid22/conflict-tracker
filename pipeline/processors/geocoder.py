from __future__ import annotations
import re
import time
from functools import lru_cache

import requests
from loguru import logger

from pipeline.config import OPENCAGE_KEY, REQUEST_TIMEOUT

OPENCAGE_URL = "https://api.opencagedata.com/geocode/v1/json"

# Simple in-memory cache: location_name → (lat, lon)
# This avoids re-calling the API for the same city repeatedly
_geocode_cache: dict[str, tuple[float, float] | None] = {}

# Countries and regions to try extracting from text
# Order matters: more specific patterns first
LOCATION_PATTERNS = [
    # City, Country
    r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?),\s*([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b",
    # "in Tehran" / "near Kyiv"
    r"\b(?:in|near|at|from|to)\s+([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b",
]

# Known location name → coordinates (common conflict locations)
# Fallback so we save API calls on frequently-seen places
KNOWN_LOCATIONS: dict[str, tuple[float, float]] = {
    "Tehran":       (35.6892, 51.3890),
    "Iran":         (32.4279, 53.6880),
    "Gaza":         (31.5017, 34.4668),
    "Gaza Strip":   (31.5017, 34.4668),
    "West Bank":    (31.9522, 35.2332),
    "Kyiv":         (50.4501, 30.5234),
    "Kiev":         (50.4501, 30.5234),
    "Ukraine":      (48.3794, 31.1656),
    "Moscow":       (55.7558, 37.6173),
    "Russia":       (61.5240, 105.3188),
    "Baghdad":      (33.3152, 44.3661),
    "Iraq":         (33.2232, 43.6793),
    "Damascus":     (33.5138, 36.2765),
    "Syria":        (34.8021, 38.9968),
    "Beirut":       (33.8938, 35.5018),
    "Lebanon":      (33.8547, 35.8623),
    "Riyadh":       (24.6877, 46.7219),
    "Saudi Arabia": (23.8859, 45.0792),
    "Jerusalem":    (31.7683, 35.2137),
    "Israel":       (31.0461, 34.8516),
    "Cairo":        (30.0444, 31.2357),
    "Egypt":        (26.8206, 30.8025),
    "Kabul":        (34.5553, 69.2075),
    "Afghanistan":  (33.9391, 67.7100),
    "Khartoum":     (15.5007, 32.5599),
    "Sudan":        (12.8628, 30.2176),
    "Mogadishu":    (2.0469, 45.3182),
    "Somalia":      (5.1521, 46.1996),
    "Tripoli":      (32.8872, 13.1913),
    "Libya":        (26.3351, 17.2283),
    "Pyongyang":    (39.0392, 125.7625),
    "North Korea":  (40.3399, 127.5101),
    "Beijing":      (39.9042, 116.4074),
    "Taiwan":       (23.6978, 120.9605),
    "Taipei":       (25.0330, 121.5654),
}


def extract_location_from_text(text: str) -> str | None:
    """
    Tries to extract a location name from article title/description.
    Returns the first match found, or None.
    """
    for pattern in LOCATION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def geocode(location_name: str) -> tuple[float, float] | None:
    """
    Converts a location name to (lat, lon).
    Checks known locations first, then the in-memory cache,
    then the OpenCage API.
    Returns None if geocoding fails.
    """
    if not location_name or not location_name.strip():
        return None

    loc = location_name.strip()

    # 1. Check hardcoded known locations (free, instant)
    for known_name, coords in KNOWN_LOCATIONS.items():
        if known_name.lower() in loc.lower():
            return coords

    # 2. Check in-memory cache
    if loc in _geocode_cache:
        return _geocode_cache[loc]

    # 3. Call OpenCage API
    if not OPENCAGE_KEY:
        return None

    try:
        resp = requests.get(
            OPENCAGE_URL,
            params={
                "q":   loc,
                "key": OPENCAGE_KEY,
                "limit": 1,
                "no_annotations": 1,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if results:
            geometry = results[0].get("geometry", {})
            lat = geometry.get("lat")
            lng = geometry.get("lng")
            if lat is not None and lng is not None:
                coords = (float(lat), float(lng))
                _geocode_cache[loc] = coords
                logger.debug(f"Geocoded '{loc}' → {coords}")
                return coords

        _geocode_cache[loc] = None
        return None

    except Exception as e:
        logger.warning(f"Geocoding failed for '{loc}': {e}")
        _geocode_cache[loc] = None
        return None


def enrich_with_geocoordinates(records: list[dict]) -> list[dict]:
    """
    Enriches records that have no lat/lon by:
    1. Using existing location_name if present
    2. Extracting location from title/description
    3. Calling geocoder
    """
    enriched = 0
    for record in records:
        # Already has coordinates — skip
        if record.get("lat") is not None and record.get("lon") is not None:
            continue

        # Try to use existing location_name
        location_name = record.get("location_name")

        # If no location_name, try to extract from text
        if not location_name:
            text = f"{record.get('title', '')} {record.get('description', '')}"
            location_name = extract_location_from_text(text)

        if not location_name:
            continue

        coords = geocode(location_name)
        if coords:
            record["location_name"] = location_name
            record["lat"]           = coords[0]
            record["lon"]           = coords[1]
            enriched += 1

        # Small delay to respect API rate limits
        time.sleep(0.05)

    logger.info(f"Geocoder enriched {enriched}/{len(records)} records with coordinates")
    return records
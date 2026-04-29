from __future__ import annotations
import hashlib
from datetime import datetime, timezone
import io
import zipfile

import requests
import pandas as pd
from loguru import logger

from pipeline.config import REQUEST_TIMEOUT

# GDELT 2.0 last-15-min update manifest URL
GDELT_MANIFEST_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

# GDELT column meanings (partial — full schema has 61 columns)
GDELT_COLUMNS = {
    1:  "event_date",
    6:  "actor1_geo_type",
    7:  "actor1_name",
    15: "actor2_geo_type",
    16: "actor2_name",
    26: "action_geo_name",
    27: "action_geo_countrycode",
    30: "action_geo_lat",
    31: "action_geo_lon",
    34: "goldstein_scale",
    53: "num_mentions",
    57: "source_url",
    58: "source_name",
}

RELEVANT_COUNTRIES = {
    "IR", "IQ", "SY", "IL", "PS", "LB", "YE", "SA", "EG",
    "UA", "RU",
    "SD", "ET", "SO", "LY", "ML", "NG",
    "AF", "PK",
    "KP", "CN", "TW",
}


def _make_hash(url: str, lat: str, lon: str) -> str:
    raw = (url + str(lat) + str(lon)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def fetch_gdelt_events() -> list[dict]:
    """
    Fetch latest GDELT event export (15 min updates),
    extract zip correctly, filter relevant countries.
    """
    try:
        # Step 1: Manifest
        manifest = requests.get(GDELT_MANIFEST_URL, timeout=REQUEST_TIMEOUT)
        manifest.raise_for_status()
        lines = manifest.text.strip().split("\n")

        csv_url = None
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3 and "export.CSV" in parts[-1]:
                csv_url = parts[-1]
                break

        if not csv_url:
            logger.error("[gdelt] Could not find export CSV in manifest")
            return []

        logger.debug(f"[gdelt] Fetching: {csv_url}")

        # Step 2: Download ZIP correctly
        resp = requests.get(csv_url, timeout=30)
        resp.raise_for_status()

        z = zipfile.ZipFile(io.BytesIO(resp.content))
        csv_name = [n for n in z.namelist() if n.endswith(".CSV")][0]

        df = pd.read_csv(
            z.open(csv_name),
            sep="\t",
            header=None,
            low_memory=False,
            on_bad_lines="skip",
        )

        if df.shape[1] < 58:
            logger.warning(f"[gdelt] Unexpected column count: {df.shape[1]}")
            return []

        # Step 3: Filter by country
        filtered = df[df.iloc[:, 27].isin(RELEVANT_COUNTRIES)]

        records = []

        for _, row in filtered.iterrows():
            try:
                source_url  = str(row.iloc[57]).strip() if pd.notna(row.iloc[57]) else ""
                location    = str(row.iloc[26]).strip() if pd.notna(row.iloc[26]) else ""
                lat         = float(row.iloc[30]) if pd.notna(row.iloc[30]) else None
                lon         = float(row.iloc[31]) if pd.notna(row.iloc[31]) else None
                actor1      = str(row.iloc[7]).strip() if pd.notna(row.iloc[7]) else ""
                actor2      = str(row.iloc[16]).strip() if pd.notna(row.iloc[16]) else ""
                goldstein   = float(row.iloc[34]) if pd.notna(row.iloc[34]) else 0.0
                event_date  = str(row.iloc[1])[:8]

                if not source_url or source_url == "nan":
                    continue

                title = f"Event: {actor1} / {actor2} in {location}".strip(" /")
                if not title or title == "Event: / in":
                    continue

                try:
                    pub_date = datetime(
                        int(event_date[:4]),
                        int(event_date[4:6]),
                        int(event_date[6:8]),
                        tzinfo=timezone.utc,
                    ).isoformat()
                except Exception:
                    pub_date = datetime.now(timezone.utc).isoformat()

                records.append({
                    "source": "gdelt",
                    "title": title[:300],
                    "description": f"Goldstein scale: {goldstein}. Actors: {actor1}, {actor2}",
                    "url": source_url,
                    "published_at": pub_date,
                    "raw_hash": _make_hash(source_url, str(lat), str(lon)),
                    "location_name": location if location and location != "nan" else None,
                    "lat": lat,
                    "lon": lon,
                    "category": "military" if goldstein < -3 else None,
                    "sentiment": None,
                    "entities": [],
                })

            except Exception as row_err:
                logger.debug(f"[gdelt] Skipping row: {row_err}")
                continue

        logger.info(f"[gdelt] {len(records)} relevant events from latest update")
        return records

    except Exception as e:
        logger.error(f"[gdelt] Fetch failed: {e}")
        return []
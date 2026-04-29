from __future__ import annotations
from loguru import logger
from pipeline.db.writer import get_existing_hashes


def deduplicate(records: list[dict]) -> list[dict]:
    """
    Removes records whose raw_hash already exists in the database.
    Also removes duplicates within the current batch.
    Returns only new, unique records.
    """
    # Fetch hashes already in DB
    db_hashes = get_existing_hashes()

    # Deduplicate within current batch too
    seen_in_batch: set[str] = set()
    new_records: list[dict] = []
    duplicate_count = 0

    for record in records:
        h = record.get("raw_hash")
        if not h:
            continue
        if h in db_hashes or h in seen_in_batch:
            duplicate_count += 1
            continue
        seen_in_batch.add(h)
        new_records.append(record)

    logger.info(
        f"Deduplication: {len(records)} in → {len(new_records)} new "
        f"({duplicate_count} duplicates removed)"
    )
    return new_records
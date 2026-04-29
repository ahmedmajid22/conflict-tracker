from __future__ import annotations
import spacy
from loguru import logger
from pipeline.config import TRACKED_ENTITIES

_nlp = None


def _get_nlp():
    """Lazy-load spaCy model (only once per process)."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
            logger.debug("spaCy model loaded")
        except OSError:
            logger.error(
                "spaCy model 'en_core_web_sm' not found. "
                "Run: python -m spacy download en_core_web_sm"
            )
            raise
    return _nlp


def extract_entities(text: str) -> list[dict]:
    """
    Runs spaCy NER on text and returns entities that match
    our tracked entities list.
    Only keeps entity types relevant to geopolitical events.
    """
    if not text or not text.strip():
        return []

    nlp = _get_nlp()
    doc = nlp(text[:5000])  # spaCy has a default limit

    relevant_types = {"PERSON", "ORG", "GPE", "NORP", "EVENT"}

    # Count occurrences of each entity
    entity_counts: dict[tuple[str, str], int] = {}
    for ent in doc.ents:
        if ent.label_ not in relevant_types:
            continue

        ent_text = ent.text.strip()
        if not ent_text:
            continue

        # Check if this entity is in our tracked list (case-insensitive partial match)
        is_tracked = any(
            tracked.lower() in ent_text.lower() or ent_text.lower() in tracked.lower()
            for tracked in TRACKED_ENTITIES
        )
        if not is_tracked:
            continue

        key = (ent_text, ent.label_)
        entity_counts[key] = entity_counts.get(key, 0) + 1

    return [
        {"name": name, "type": etype, "count": count}
        for (name, etype), count in entity_counts.items()
    ]


def enrich_with_entities(records: list[dict]) -> list[dict]:
    """
    Runs NER on all records and adds extracted entities.
    """
    total_entities = 0
    for record in records:
        text = f"{record.get('title', '')} {record.get('description', '')}"
        entities = extract_entities(text)
        record["entities"] = entities
        total_entities += len(entities)

    logger.info(f"NER extracted {total_entities} entity mentions across {len(records)} records")
    return records
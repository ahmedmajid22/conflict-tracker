from __future__ import annotations
import time

import requests
from loguru import logger

from pipeline.config import HF_API_TOKEN, HF_API_URL, HF_TIMEOUT

# Map HuggingFace labels to human-readable labels
_LABEL_MAP = {
    "LABEL_0": "negative",
    "LABEL_1": "positive",
    "NEGATIVE": "negative",
    "POSITIVE": "positive",
    "negative": "negative",
    "positive": "positive",
    "neutral":  "neutral",
}


def _score_from_label(label: str, confidence: float) -> float:
    """
    Converts label + confidence to a -1 to +1 score:
      negative → negative score
      neutral  → near-zero score
      positive → positive score
    """
    l = label.lower()
    if "negative" in l:
        return -confidence
    if "positive" in l:
        return confidence
    return 0.0  # neutral


def analyze_sentiment(text: str) -> dict:
    """
    Calls the HuggingFace Inference API to get sentiment.
    Returns dict with keys: label, score, model_name.
    Falls back to neutral on any error.
    """
    neutral_result = {
        "label":      "neutral",
        "score":      0.0,
        "model_name": "fallback",
    }

    if not HF_API_TOKEN:
        return neutral_result

    if not text or not text.strip():
        return neutral_result

    # HuggingFace models have a max input of 512 tokens (~500 chars safely)
    truncated_text = text.strip()[:500]

    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": truncated_text}

    for attempt in range(3):  # Retry up to 3 times
        try:
            resp = requests.post(
                HF_API_URL,
                headers=headers,
                json=payload,
                timeout=HF_TIMEOUT,
            )

            # Model may be loading (503) — wait and retry
            if resp.status_code == 503:
                wait = 10 * (attempt + 1)
                logger.debug(f"[sentiment] Model loading, retrying in {wait}s...")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            results = resp.json()

            # Results is a list of lists (batch response)
            if isinstance(results, list) and results:
                inner = results[0] if isinstance(results[0], list) else results
                best = max(inner, key=lambda x: x.get("score", 0))
                raw_label = best.get("label", "neutral")
                label = _LABEL_MAP.get(raw_label, "neutral")
                confidence = float(best.get("score", 0.5))
                return {
                    "label":      label,
                    "score":      round(_score_from_label(label, confidence), 4),
                    "model_name": "cardiffnlp/twitter-roberta-base-sentiment",
                }

        except requests.exceptions.Timeout:
            logger.warning(f"[sentiment] Timeout on attempt {attempt + 1}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"[sentiment] Error: {e}")
            break

    return neutral_result


def enrich_with_sentiment(records: list[dict]) -> list[dict]:
    """
    Runs sentiment analysis on every record.
    Adds 'sentiment' dict to each record.
    """
    processed = 0
    for i, record in enumerate(records):
        text = f"{record.get('title', '')}. {record.get('description', '')}"
        record["sentiment"] = analyze_sentiment(text)
        processed += 1

        # Small delay between API calls to be polite with the free tier
        if i > 0 and i % 5 == 0:
            time.sleep(1)

    logger.info(f"Sentiment analysis completed for {processed} records")
    return records
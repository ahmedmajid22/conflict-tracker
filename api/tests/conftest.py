"""
Shared pytest fixtures for the API test suite.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from api.main import app
from api.dependencies import get_supabase


# ── Mock Supabase client ─────────────────────────────────
@pytest.fixture
def mock_supabase():
    """
    Returns a MagicMock that mimics the Supabase client.
    The chain .table().select().order().range().execute() all return mocks.
    We configure .data on the final .execute() mock to return test data.
    """
    mock = MagicMock()

    # Build a chainable mock — every method returns the same mock
    # so we can chain .table().select().order().eq().execute()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.order.return_value = mock
    mock.range.return_value = mock
    mock.limit.return_value = mock
    mock.eq.return_value = mock
    mock.gte.return_value = mock
    mock.lte.return_value = mock
    mock.not_.return_value = mock
    mock.is_.return_value = mock
    mock.or_.return_value = mock
    mock.single.return_value = mock
    mock.rpc.return_value = mock

    # Default: return empty data
    mock.execute.return_value.data = []
    mock.execute.return_value.count = 0

    return mock


@pytest.fixture
def client(mock_supabase):
    """
    Returns a FastAPI TestClient with the Supabase dependency overridden
    to use our mock, and the cache disabled.
    """
    app.dependency_overrides[get_supabase] = lambda: mock_supabase

    with patch("api.cache.cache_get", return_value=None), \
         patch("api.cache.cache_set", return_value=None):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


# ── Sample test data ─────────────────────────────────────
SAMPLE_EVENT = {
    "id":            "00000000-0000-0000-0000-000000000001",
    "source":        "bbc",
    "title":         "Airstrike reported near capital",
    "description":   "Military aircraft conducted strikes on infrastructure.",
    "url":           "https://bbc.com/news/world/test-article",
    "published_at":  "2024-06-01T12:00:00+00:00",
    "location_name": "Baghdad",
    "lat":           33.3152,
    "lon":           44.3661,
    "category":      "military",
    "raw_hash":      "abc123",
    "is_processed":  True,
    "sentiment": [
        {"score": -0.85, "label": "negative", "model_name": "cardiffnlp/twitter-roberta-base-sentiment"}
    ],
}

SAMPLE_SENTIMENT_DAILY = [
    {"date": "2024-05-30", "avg_score": -0.45, "neg_count": 12, "neu_count": 5, "pos_count": 2, "event_count": 19},
    {"date": "2024-05-31", "avg_score": -0.62, "neg_count": 18, "neu_count": 3, "pos_count": 1, "event_count": 22},
    {"date": "2024-06-01", "avg_score": -0.38, "neg_count": 9,  "neu_count": 6, "pos_count": 3, "event_count": 18},
]
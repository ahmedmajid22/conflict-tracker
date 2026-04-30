import pytest
from api.tests.conftest import SAMPLE_SENTIMENT_DAILY


class TestSentimentTrend:
    def test_returns_200(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = SAMPLE_SENTIMENT_DAILY
        response = client.get("/analytics/sentiment-trend")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert body["count"] == 3

    def test_days_param_accepted(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/analytics/sentiment-trend?days=30")
        assert response.status_code == 200
        assert response.json()["days"] == 30

    def test_invalid_days_too_small_returns_422(self, client):
        response = client.get("/analytics/sentiment-trend?days=1")
        assert response.status_code == 422


class TestCategoryBreakdown:
    def test_returns_200(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = [
            {"category": "military", "count": 45},
            {"category": "diplomatic", "count": 20},
        ]
        response = client.get("/analytics/category-breakdown")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert len(body["data"]) == 2


class TestEventVolume:
    def test_returns_200(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = SAMPLE_SENTIMENT_DAILY
        response = client.get("/analytics/volume")
        assert response.status_code == 200
        assert "data" in response.json()

    def test_days_param_accepted(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/analytics/volume?days=14")
        assert response.status_code == 200
        assert response.json()["days"] == 14


class TestKpiSummary:
    def test_returns_200_with_all_keys(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = [
            {"source": "bbc", "category": "military", "avg_score": -0.5}
        ]
        mock_supabase.execute.return_value.count = 100

        response = client.get("/analytics/kpi")
        assert response.status_code == 200
        body = response.json()
        expected_keys = {
            "total_events", "today_events", "avg_sentiment_7d",
            "top_source", "top_category",
        }
        assert expected_keys.issubset(body.keys())


class TestTopEntities:
    def test_returns_200(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = [
            {"name": "Iran", "type": "GPE", "count": 5, "events": {"published_at": "2024-06-01"}},
            {"name": "Russia", "type": "GPE", "count": 3, "events": {"published_at": "2024-06-01"}},
        ]
        response = client.get("/analytics/top-entities")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body

    def test_type_filter_accepted(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/analytics/top-entities?type=GPE")
        assert response.status_code == 200
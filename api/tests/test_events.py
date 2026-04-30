import pytest
from api.tests.conftest import SAMPLE_EVENT


class TestListEvents:
    def test_returns_200_with_empty_data(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/events")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert body["data"] == []
        assert body["count"] == 0

    def test_returns_events(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = [SAMPLE_EVENT]
        response = client.get("/events")
        assert response.status_code == 200
        body = response.json()

        assert "data" in body
        assert "count" in body
        assert "limit" in body
        assert "offset" in body


    def test_pagination_params_accepted(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/events?limit=10&offset=20")
        assert response.status_code == 200
        body = response.json()
        assert body["limit"] == 10
        assert body["offset"] == 20

    def test_limit_capped_at_200(self, client, mock_supabase):
        # FastAPI enforces le=200 via Query validation — anything over 200 returns 422
        mock_supabase.execute.return_value.data = []

        response = client.get("/events?limit=200")
        assert response.status_code == 200

        response_over = client.get("/events?limit=201")
        assert response_over.status_code == 422

    def test_category_filter_accepted(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = [SAMPLE_EVENT]
        response = client.get("/events?category=military")
        assert response.status_code == 200

    def test_date_filter_accepted(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/events?from_date=2024-01-01&to_date=2024-12-31")
        assert response.status_code == 200

    def test_geolocated_filter_accepted(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = [SAMPLE_EVENT]
        response = client.get("/events?geolocated=true")
        assert response.status_code == 200

    def test_search_filter_accepted(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/events?search=airstrike")
        assert response.status_code == 200

    def test_invalid_limit_returns_422(self, client):
        response = client.get("/events?limit=0")
        assert response.status_code == 422

    def test_invalid_offset_returns_422(self, client):
        response = client.get("/events?offset=-1")
        assert response.status_code == 422


class TestMapEvents:
    def test_returns_200(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = [SAMPLE_EVENT]
        response = client.get("/events/map")
        assert response.status_code == 200
        body = response.json()

        assert "data" in body
        assert "count" in body

    def test_days_param_accepted(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/events/map?days=7")
        assert response.status_code == 200

    def test_invalid_days_returns_422(self, client):
        response = client.get("/events/map?days=0")
        assert response.status_code == 422


class TestGetEvent:
    def test_returns_event_by_id(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = SAMPLE_EVENT
        event_id = SAMPLE_EVENT["id"]
        response = client.get(f"/events/{event_id}")
        assert response.status_code == 200

    def test_returns_404_when_not_found(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = None
        response = client.get("/events/nonexistent-id")
        assert response.status_code == 404
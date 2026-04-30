class TestHealthCheck:
    def test_returns_200(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = [
            {
                "run_at":      "2024-06-01T12:00:00+00:00",
                "inserted":    25,
                "fetched":     80,
                "duration_ms": 45000,
            }
        ]
        response = client.get("/health")
        assert response.status_code == 200

    def test_has_required_fields(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/health")
        body = response.json()
        for field in ("api", "database", "cache", "pipeline", "timestamp"):
            assert field in body, f"Missing field: {field}"

    def test_api_status_is_ok(self, client, mock_supabase):
        mock_supabase.execute.return_value.data = []
        response = client.get("/health")
        assert response.json()["api"] == "ok"

    def test_ping_returns_pong(self, client):
        response = client.get("/health/ping")
        assert response.status_code == 200
        assert response.json()["status"] == "pong"


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert "name" in body
        assert "docs" in body
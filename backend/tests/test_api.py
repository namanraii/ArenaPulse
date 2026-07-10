"""Integration tests for FastAPI endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz_returns_ok() -> None:
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "FIFA World Cup 2026" in data["tournament"]


def test_demo_navigation_endpoint() -> None:
    response = client.post(
        "/api/v1/demo/navigate",
        json={
            "start_location": "Section_214",
            "destination_intent": "nearest_restroom",
            "step_free": True,
            "language": "es",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["step_free"] is True
    assert len(data["explanation"]) > 10


def test_demo_concierge_endpoint() -> None:
    response = client.post(
        "/api/v1/demo/concierge/chat",
        json={"message": "Where is the metro?", "language": "en"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["detected_intent"] == "transit"
    assert len(data["response"]) > 5


def test_sustainability_summary_public() -> None:
    response = client.get("/api/v1/sustainability/summary")
    assert response.status_code == 200
    data = response.json()
    assert "transit_split" in data
    assert "sustainability_score" in data


def test_demo_zones_returns_list() -> None:
    response = client.get("/api/v1/demo/zones")
    assert response.status_code == 200
    zones = response.json()
    assert isinstance(zones, list)
    assert len(zones) >= 6


def test_efficiency_metrics_requires_auth() -> None:
    response = client.get("/api/v1/ops/efficiency")
    assert response.status_code == 401

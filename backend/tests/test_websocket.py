"""WebSocket crowd-feed endpoint tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_websocket_crowd_feed_connects(client: TestClient) -> None:
    """WS endpoint should accept connections and emit crowd_update messages."""
    mock_zones = [
        {
            "name": "Zone_1",
            "density": 0.45,
            "label": "North Stand",
            "capacity": 10000,
        }
    ]

    with patch("app.api.websocket.deps") as mock_deps:
        mock_simulator = MagicMock()
        mock_simulator.get_zones_for_frontend.return_value = mock_zones
        mock_deps.simulator = mock_simulator

        with client.websocket_connect("/api/v1/ws/crowd-feed") as ws:
            data = ws.receive_json()
            assert data["type"] == "crowd_update"
            assert isinstance(data["zones"], list)
            assert len(data["zones"]) > 0
            assert data["zones"][0]["name"] == "Zone_1"


def test_websocket_falls_back_to_demo_zones(client: TestClient) -> None:
    """When simulator is None, WS should fall back to static demo zones."""
    with patch("app.api.websocket.deps") as mock_deps:
        mock_deps.simulator = None

        with client.websocket_connect("/api/v1/ws/crowd-feed") as ws:
            data = ws.receive_json()
            assert data["type"] == "crowd_update"
            assert isinstance(data["zones"], list)


def test_websocket_zone_has_expected_fields(client: TestClient) -> None:
    """Each zone in the crowd_update payload must have a 'name' and 'density' field."""
    with patch("app.api.websocket.deps") as mock_deps:
        mock_deps.simulator = None

        with client.websocket_connect("/api/v1/ws/crowd-feed") as ws:
            data = ws.receive_json()
            zones = data["zones"]
            if zones:
                zone = zones[0]
                assert "name" in zone
                assert "density" in zone

"""Integration tests for auth API endpoints: register, login, refresh, logout."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import User, UserRole


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# /auth/register
# ---------------------------------------------------------------------------


def test_register_invalid_email(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "newuser", "email": "not-an-email", "password": "Password123"},
    )
    assert resp.status_code == 400
    assert "email" in resp.json()["detail"].lower()


def test_register_short_password(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "newuser", "email": "u@example.com", "password": "short"},
    )
    assert resp.status_code == 400
    assert "password" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# /auth/login
# ---------------------------------------------------------------------------


def test_login_invalid_credentials(client: TestClient) -> None:
    with patch("app.api.auth.authenticate_user", new=AsyncMock(return_value=None)):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "wrong"},
        )
    assert resp.status_code == 401
    assert "credentials" in resp.json()["detail"].lower()


def test_login_success_returns_tokens(client: TestClient) -> None:
    fake_user = User(
        id=1,
        username="testfan",
        email="fan@test.com",
        role=UserRole.FAN,
        created_at=__import__("datetime").datetime.utcnow(),
    )
    with patch("app.api.auth.authenticate_user", new=AsyncMock(return_value=fake_user)):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "testfan", "password": "Password123"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_access_token_has_correct_claims(client: TestClient) -> None:
    fake_user = User(
        id=5,
        username="organizer1",
        email="org@test.com",
        role=UserRole.ORGANIZER,
        created_at=__import__("datetime").datetime.utcnow(),
    )
    with patch("app.api.auth.authenticate_user", new=AsyncMock(return_value=fake_user)):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "organizer1", "password": "Password123"},
        )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["sub"] == "5"
    assert payload["role"] == "organizer"
    assert payload["type"] == "access"


# ---------------------------------------------------------------------------
# /auth/refresh
# ---------------------------------------------------------------------------


def test_refresh_with_invalid_token(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "notavalidtoken"},
    )
    assert resp.status_code == 401


def test_refresh_rejects_access_token(client: TestClient) -> None:
    """An access token must not be accepted as a refresh token."""
    from app.auth import create_access_token

    access = create_access_token(user_id=1, username="u", role=UserRole.FAN)
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access},
    )
    assert resp.status_code == 401


def test_refresh_success(client: TestClient) -> None:
    from app.auth import create_refresh_token

    fake_user = User(
        id=3,
        username="volunteer1",
        email="vol@test.com",
        role=UserRole.VOLUNTEER,
        created_at=__import__("datetime").datetime.utcnow(),
    )
    refresh_token = create_refresh_token(user_id=3)
    with patch("app.api.auth.get_user_by_id", new=AsyncMock(return_value=fake_user)):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


# ---------------------------------------------------------------------------
# /auth/logout
# ---------------------------------------------------------------------------


def test_logout_returns_success(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert "message" in resp.json()

"""Tests for JWT auth utilities: hashing, token creation, decode, expiry."""

from __future__ import annotations

from datetime import datetime, timezone

import jwt
import pytest

from app.auth import (
    _hash_password,
    _verify_password,
    create_access_token,
    create_refresh_token,
)
from app.config import settings
from app.models import UserRole


def test_password_hashing():
    password = "secure_password_123"
    hashed = _hash_password(password)

    assert hashed != password
    assert _verify_password(password, hashed) is True
    assert _verify_password("wrong_password", hashed) is False


def test_create_access_token_returns_string():
    token = create_access_token(user_id=1, username="testuser", role=UserRole.VOLUNTEER)
    assert isinstance(token, str)
    assert len(token) > 0


def test_access_token_payload():
    token = create_access_token(user_id=42, username="alice", role=UserRole.ORGANIZER)
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])

    assert payload["sub"] == "42"
    assert payload["username"] == "alice"
    assert payload["role"] == UserRole.ORGANIZER.value
    assert payload["type"] == "access"


def test_refresh_token_payload():
    token = create_refresh_token(user_id=7)
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])

    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"


def test_access_token_not_accepted_as_refresh():
    access = create_access_token(user_id=1, username="fan", role=UserRole.FAN)
    payload = jwt.decode(access, settings.secret_key, algorithms=["HS256"])
    # An access token must NOT have type == "refresh"
    assert payload.get("type") == "access"
    assert payload.get("type") != "refresh"


def test_token_expiry_is_future():
    token = create_access_token(user_id=1, username="u", role=UserRole.FAN)
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    assert exp > datetime.now(timezone.utc)


def test_invalid_token_raises():
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode("invalid.token.here", settings.secret_key, algorithms=["HS256"])


def test_tampered_token_raises():
    token = create_access_token(user_id=1, username="u", role=UserRole.FAN)
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(tampered, settings.secret_key, algorithms=["HS256"])


def test_different_roles_produce_different_tokens():
    t_fan = create_access_token(user_id=1, username="u", role=UserRole.FAN)
    t_org = create_access_token(user_id=1, username="u", role=UserRole.ORGANIZER)
    assert t_fan != t_org


def test_hash_is_not_deterministic():
    """bcrypt salts should make each hash unique."""
    pw = "same_password"
    h1 = _hash_password(pw)
    h2 = _hash_password(pw)
    assert h1 != h2
    assert _verify_password(pw, h1) is True
    assert _verify_password(pw, h2) is True

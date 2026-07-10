import pytest
from app.auth import _hash_password, _verify_password, create_access_token
from app.models import UserRole

def test_password_hashing():
    password = "secure_password_123"
    hashed = _hash_password(password)
    
    assert hashed != password
    assert _verify_password(password, hashed) is True
    assert _verify_password("wrong_password", hashed) is False

def test_create_access_token():
    data = {"sub": "testuser"}
    token = create_access_token(data, username="testuser", role=UserRole.VOLUNTEER)
    
    assert isinstance(token, str)
    assert len(token) > 0

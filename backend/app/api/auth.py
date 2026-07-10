"""Authentication API routes."""

from __future__ import annotations

import re

import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth import _hash_password, authenticate_user, create_access_token, create_refresh_token
from app.config import settings
from app.database import create_user, get_user_by_id, get_user_by_username
from app.models import Token, User, UserRole
from app.utils.security import public_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=User)
async def register(req: RegisterRequest, request: Request) -> User:
    """Register a new user account.

    Args:
        req: Registration details.
        request: The HTTP request.

    Returns:
        User: The created user object.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not await public_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests")

    if not re.match(r"[^@]+@[^@]+\.[^@]+", req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    role = UserRole.FAN
    existing = await get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    hashed = _hash_password(req.password)
    return await create_user(req.username, req.email, hashed, role)


@router.post("/login", response_model=Token)
async def login(req: LoginRequest, request: Request) -> Token:
    """Authenticate a user and return tokens.

    Args:
        req: Login credentials.
        request: The HTTP request.

    Returns:
        Token: Access and refresh tokens.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not await public_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests")

    user = await authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = create_access_token(user.id, user.username, user.role)
    refresh = create_refresh_token(user.id)
    return Token(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=Token)
async def refresh(req: RefreshRequest) -> Token:
    """Refresh an access token using a valid refresh token."""
    try:
        payload = jwt.decode(req.refresh_token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Not a refresh token")
        user_id = int(payload["sub"])
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(user.id, user.username, user.role)
        new_refresh = create_refresh_token(user.id)
        return Token(access_token=access, refresh_token=new_refresh)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
async def logout() -> dict:
    """Log out a user.

    Returns:
        dict: Success message.
    """
    return {"message": "Logged out successfully"}

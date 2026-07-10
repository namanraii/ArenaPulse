"""ArenaPulse backend application configuration."""

from __future__ import annotations

import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini / LLM
    gemini_api_key: str = ""
    gemini_flash_url: str = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash-exp:generateContent"
    )
    gemini_pro_url: str = (
        "https://generativelanguage.googleapis.com/v1beta/models/" "gemini-1.5-pro:generateContent"
    )

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "arenapulse123"

    # PostgreSQL
    database_url: str = "postgresql://arenapulse:arenapulse123@localhost:5432/arenapulse"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = secrets.token_urlsafe(32)
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()

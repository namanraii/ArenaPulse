"""Async PostgreSQL database layer."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from app.config import settings
from app.models import (
    OpsAction,
    OpsActionPriority,
    OpsActionStatus,
    User,
    UserRole,
)

_pool: asyncpg.Pool | None = None


async def init_db() -> None:
    """Initialize the PostgreSQL connection pool and schema."""
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'fan',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id SERIAL PRIMARY KEY,
                zone TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                resolved_at TIMESTAMP WITH TIME ZONE,
                action_taken TEXT
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ops_actions (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'pending',
                recommended_by TEXT NOT NULL,
                approved_by INTEGER REFERENCES users(id),
                approved_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                affected_zones TEXT[] DEFAULT '{}',
                affected_population INTEGER DEFAULT 0,
                time_to_impact_min REAL
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                action_type TEXT NOT NULL,
                target_id TEXT,
                details JSONB DEFAULT '{}',
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id SERIAL PRIMARY KEY,
                session_token TEXT UNIQUE NOT NULL,
                language TEXT DEFAULT 'en',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """
        )
    await seed_demo_users()


async def close_db() -> None:
    """Close the PostgreSQL connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a database connection from the pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    async with _pool.acquire() as conn:
        yield conn


async def create_user(username: str, email: str, hashed_password: str, role: UserRole) -> User:
    """Create a new user in the database.

    Args:
        username: The unique username.
        email: The unique email address.
        hashed_password: The securely hashed password.
        role: The user's role.

    Returns:
        User: The newly created user.
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (username, email, hashed_password, role)
            VALUES ($1, $2, $3, $4)
            RETURNING id, username, email, role, created_at
            """,
            username,
            email,
            hashed_password,
            role.value,
        )
        return User(**row)


async def get_user_by_username(username: str) -> User | None:
    """Retrieve a user by their username.

    Args:
        username: The username to search for.

    Returns:
        User | None: The user if found, else None.
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, email, role, created_at FROM users WHERE username = $1",
            username,
        )
        return User(**row) if row else None


async def get_user_by_id(user_id: int) -> User | None:
    """Retrieve a user by their ID.

    Args:
        user_id: The ID of the user.

    Returns:
        User | None: The user if found, else None.
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, email, role, created_at FROM users WHERE id = $1",
            user_id,
        )
        return User(**row) if row else None


async def create_ops_action(
    title: str,
    description: str,
    reasoning: str,
    priority: OpsActionPriority,
    recommended_by: str,
    affected_zones: list[str],
    affected_population: int,
    time_to_impact_min: float | None = None,
) -> OpsAction:
    """Create a new operational action in the database.

    Args:
        title: Short title of the action.
        description: Detailed description of the action.
        reasoning: Rationale for recommending this action.
        priority: Priority level of the action.
        recommended_by: The agent or user who recommended this action.
        affected_zones: List of zones affected.
        affected_population: Estimated number of people affected.
        time_to_impact_min: Estimated time in minutes until impact.

    Returns:
        OpsAction: The newly created operational action.
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO ops_actions
            (title, description, reasoning, priority, recommended_by,
             affected_zones, affected_population, time_to_impact_min)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            title,
            description,
            reasoning,
            priority.value,
            recommended_by,
            affected_zones,
            affected_population,
            time_to_impact_min,
        )
        return _row_to_ops_action(row)


async def get_pending_ops_actions() -> list[OpsAction]:
    """Retrieve all operational actions with a 'pending' status.

    Returns:
        list[OpsAction]: A list of pending operational actions, ordered by creation time descending.
    """
    async with get_db() as conn:
        rows = await conn.fetch(
            "SELECT * FROM ops_actions WHERE status = 'pending' ORDER BY created_at DESC"
        )
        return [_row_to_ops_action(r) for r in rows]


async def get_all_ops_actions(limit: int = 100) -> list[OpsAction]:
    """Retrieve all operational actions up to a specified limit.

    Args:
        limit: Maximum number of actions to retrieve (default: 100).

    Returns:
        list[OpsAction]: A list of operational actions, ordered by creation time descending.
    """
    async with get_db() as conn:
        rows = await conn.fetch(
            "SELECT * FROM ops_actions ORDER BY created_at DESC LIMIT $1",
            limit,
        )
        return [_row_to_ops_action(r) for r in rows]


async def update_ops_action_status(
    action_id: int,
    status: OpsActionStatus,
    approved_by: int | None = None,
) -> OpsAction | None:
    """Update the status of an operational action.

    Args:
        action_id: The ID of the action to update.
        status: The new status to apply.
        approved_by: The ID of the user approving the action, if applicable.

    Returns:
        OpsAction | None: The updated action, or None if the action wasn't found.
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            UPDATE ops_actions
            SET status = $1, approved_by = $2, approved_at = NOW()
            WHERE id = $3
            RETURNING *
            """,
            status.value,
            approved_by,
            action_id,
        )
        return _row_to_ops_action(row) if row else None


async def add_audit_log(
    user_id: int | None,
    action_type: str,
    target_id: str | None = None,
    details: dict | None = None,
) -> None:
    """Add a new audit log entry.

    Args:
        user_id: The ID of the user performing the action, if any.
        action_type: A string describing the action.
        target_id: The ID of the entity targeted by the action.
        details: Additional contextual data as a dictionary.
    """
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO audit_logs (user_id, action_type, target_id, details)
            VALUES ($1, $2, $3, $4)
            """,
            user_id,
            action_type,
            target_id,
            details or {},
        )


async def get_audit_logs(limit: int = 200) -> list[dict]:
    """Retrieve audit logs up to a specified limit.

    Args:
        limit: Maximum number of logs to retrieve (default: 200).

    Returns:
        list[dict]: A list of audit log records.
    """
    async with get_db() as conn:
        rows = await conn.fetch(
            """
            SELECT a.id, a.user_id, u.username, a.action_type, a.target_id,
                   a.details, a.timestamp
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.timestamp DESC
            LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in rows]


def _row_to_ops_action(row: asyncpg.Record) -> OpsAction:
    """Convert an asyncpg database record into an OpsAction Pydantic model.

    Args:
        row: The asyncpg database record.

    Returns:
        OpsAction: The converted OpsAction object.
    """
    return OpsAction(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        reasoning=row["reasoning"],
        priority=OpsActionPriority(row["priority"]),
        status=OpsActionStatus(row["status"]),
        recommended_by=row["recommended_by"],
        approved_by=row["approved_by"],
        approved_at=row["approved_at"],
        created_at=row["created_at"],
        affected_zones=list(row["affected_zones"]),
        affected_population=row["affected_population"],
        time_to_impact_min=row["time_to_impact_min"],
    )


async def seed_demo_users() -> None:
    """Seed default demo accounts for judges and local development."""
    from app.auth import _hash_password

    demo_users = [
        ("organizer", "organizer@arenapulse.local", UserRole.ORGANIZER),
        ("volunteer", "volunteer@arenapulse.local", UserRole.VOLUNTEER),
        ("fan", "fan@arenapulse.local", UserRole.FAN),
    ]
    password_hash = _hash_password("password")
    async with get_db() as conn:
        for username, email, role in demo_users:
            await conn.execute(
                """
                INSERT INTO users (username, email, hashed_password, role)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (username) DO NOTHING
                """,
                username,
                email,
                password_hash,
                role.value,
            )
        # Seed starter ops actions if table is empty
        count = await conn.fetchval("SELECT COUNT(*) FROM ops_actions")
        if count == 0:
            from app.demo_data import demo_ops_actions

            for action in demo_ops_actions():
                await conn.execute(
                    """
                    INSERT INTO ops_actions
                    (title, description, reasoning, priority, status, recommended_by,
                     affected_zones, affected_population, time_to_impact_min)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    action.title,
                    action.description,
                    action.reasoning,
                    action.priority.value,
                    action.status.value,
                    action.recommended_by,
                    action.affected_zones,
                    action.affected_population,
                    action.time_to_impact_min,
                )

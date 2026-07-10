"""Top-level conftest: mock asyncpg and neo4j before any app module is imported.

asyncpg does not support Python 3.13 yet. This stub replaces the module so
tests can import app code without a compiled asyncpg wheel.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock


def _make_asyncpg_stub() -> ModuleType:
    """Return a minimal asyncpg stand-in."""
    mod = ModuleType("asyncpg")
    # Pool / connection mocks
    pool = MagicMock()
    pool.close = AsyncMock()
    pool.acquire = MagicMock(
        return_value=MagicMock(
            __aenter__=AsyncMock(
                return_value=MagicMock(
                    execute=AsyncMock(),
                    fetch=AsyncMock(return_value=[]),
                    fetchrow=AsyncMock(return_value=None),
                    fetchval=AsyncMock(return_value=None),
                )
            ),
            __aexit__=AsyncMock(return_value=False),
        )
    )
    mod.create_pool = AsyncMock(return_value=pool)
    mod.Pool = type("Pool", (), {})
    mod.Connection = type("Connection", (), {})
    mod.Record = dict
    mod.exceptions = ModuleType("asyncpg.exceptions")
    mod.exceptions.UniqueViolationError = Exception
    sys.modules["asyncpg"] = mod
    sys.modules["asyncpg.exceptions"] = mod.exceptions
    import app.database

    app.database._pool = pool
    return mod


# Install stubs BEFORE any app.* import
_make_asyncpg_stub()

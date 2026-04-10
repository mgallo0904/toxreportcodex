"""Database configuration and session management.

This module exposes a SQLAlchemy asynchronous engine and session factory
configured via the application settings. It also provides a dependency
for FastAPI routes to access a database session using `get_db`.

NOTE: The SQLAlchemy package is not installed in this environment. This
module is provided as a reference implementation and will not function
without the appropriate dependencies. It should be tested and executed
within an environment where `sqlalchemy[asyncio]` and its drivers are
available.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

from pydantic import BaseModel
from .config import get_settings

try:
    # SQLAlchemy imports are optional to avoid ImportError at import time
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
except Exception as exc:  # pragma: no cover - fall back if not installed
    AsyncSession = None  # type: ignore
    create_async_engine = None  # type: ignore
    sessionmaker = None  # type: ignore


settings = get_settings()

if create_async_engine is not None:
    # Create an asynchronous engine using the configured database URL
    engine = create_async_engine(settings.database_url, echo=False, future=True)
    # Create a session factory bound to the engine
    async_session_factory = sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
else:
    engine = None
    async_session_factory = None  # type: ignore


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an asynchronous database session.

    This helper ensures that a session is created for each request and
    automatically closed when the request is finished. The function is
    intentionally a generator to integrate with FastAPI's dependency
    injection system.

    Yields
    ------
    AsyncSession
        A transactional SQLAlchemy session.
    """
    if async_session_factory is None:
        raise RuntimeError("SQLAlchemy is not installed. Database operations are unavailable.")
    async with async_session_factory() as session:
        yield session
"""Alembic environment configuration.

This script configures Alembic for running migrations in both offline
and online modes with an asynchronous SQLAlchemy engine. Alembic will
detect the metadata from the ORM models and generate migrations
accordingly.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context

from ..config import get_settings
from ..models import Base  # import all metadata

# Interpret the config file for Python logging.
config = context.config
fileConfig(config.config_file_name)

# Get settings and set the SQLAlchemy URL for migrations
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable: AsyncEngine = context.config.attributes.get("connection")

    if connectable is None:
        from sqlalchemy.ext.asyncio import create_async_engine

        connectable = create_async_engine(settings.database_url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        await connection.run_sync(do_run_migrations)


def do_run_migrations(connection: Connection) -> None:
    with context.begin_transaction():
        context.run_migrations()


def run_migrations() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())


run_migrations()
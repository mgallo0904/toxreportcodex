"""Base declarative model for SQLAlchemy.

All ORM models inherit from the `Base` class defined here. This
centralises the metadata registry and simplifies table creation across
the application. SQLAlchemy's 2.0 style `DeclarativeBase` is used to
support Python type checking and future proofing.
"""

from __future__ import annotations

import uuid
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    # Provide a default primary key generation method to avoid repeating
    # `default=uuid.uuid4` in every model definition. Subclasses can
    # override this by specifying their own Column defaults.
    @staticmethod
    def generate_uuid() -> uuid.UUID:
        return uuid.uuid4()
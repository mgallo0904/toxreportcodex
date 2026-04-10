"""SQLAlchemy model registry.

This module exposes the declarative `Base` class and imports all model
definitions to ensure they are registered with SQLAlchemy's metadata. New
models should be added here to participate in table creation and Alembic
migrations.
"""

from .base import Base  # noqa: F401
from .session import Session  # noqa: F401
from .document import Document  # noqa: F401
from .chunk import Chunk  # noqa: F401
from .section import DocumentSection  # noqa: F401
from .claim import Claim  # noqa: F401
from .conflict import Conflict  # noqa: F401
from .finding import Finding  # noqa: F401
from .clarification import Clarification  # noqa: F401
from .finetune import FinetuneJob  # noqa: F401
from .model_config import ModelConfig  # noqa: F401
"""Schemas for document resources.

Defines the Pydantic models used for serialising documents in API
responses and updating their properties. Documents are attached to
sessions and contain metadata about uploaded files.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Representation of a document returned from the API."""

    id: uuid.UUID
    session_id: uuid.UUID
    original_filename: str
    format: str
    assigned_role: Optional[str] = None
    role_label: Optional[str] = None
    total_pages: Optional[int] = None
    total_chunks: Optional[int] = None
    created_at: datetime

    class Config:
        orm_mode = True


class DocumentUpdate(BaseModel):
    """Fields that can be updated on a document."""

    assigned_role: Optional[str] = Field(default=None)
    role_label: Optional[str] = Field(default=None)
"""Pydantic schemas for conflict resources.

Conflicts arise when two documents report different values for the
same parameter.  This schema includes fields for both values and
references to the source documents and chunks.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel


class ConflictResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    parameter_name: str
    value_a: Optional[str] = None
    document_id_a: Optional[uuid.UUID] = None
    document_name_a: Optional[str] = None
    chunk_id_a: Optional[uuid.UUID] = None
    page_a: Optional[int] = None
    value_b: Optional[str] = None
    document_id_b: Optional[uuid.UUID] = None
    document_name_b: Optional[str] = None
    chunk_id_b: Optional[uuid.UUID] = None
    page_b: Optional[int] = None
    resolved: bool

    class Config:
        orm_mode = True
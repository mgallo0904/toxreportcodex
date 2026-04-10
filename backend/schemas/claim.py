"""Pydantic schemas for claim resources.

These schemas serialise claims extracted during Pass 1 for API
responses.  Claims can represent numerical values, abbreviations,
conclusions or methods depending on the `parameter_type` field.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class ClaimResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    parameter_type: str
    parameter_name: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    context_sentence: Optional[str] = None
    page_number: Optional[int] = None

    class Config:
        orm_mode = True
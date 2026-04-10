"""Pydantic schemas for document section resources.

These schemas represent hierarchical outlines of documents created
during Pass 1.  Each section includes its header text, optional page
number, section level, and any child sections.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class SectionNode(BaseModel):
    """Recursive representation of a document section."""

    id: uuid.UUID
    chunk_id: uuid.UUID
    header: str = Field(..., alias="header_text")
    page: Optional[int] = Field(None, alias="page_number")
    level: int = Field(..., alias="section_level")
    children: List['SectionNode'] = []

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class DocumentOutline(BaseModel):
    """Outline of a single document including its sections."""

    id: uuid.UUID
    filename: str
    role: Optional[str] = None
    sections: List[SectionNode]

    class Config:
        orm_mode = True
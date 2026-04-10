"""Schemas for session resources.

These Pydantic models define the structure of request and response
bodies for the session API endpoints. SessionCreate is used to
create a new session. SessionSummary represents a list item in the
sessions index endpoint, while SessionDetail contains full details for
a single session including attached documents.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Request body for creating a new session."""

    study_name: Optional[str] = Field(default=None, description="Optional name of the study.")
    study_type: str = Field(..., description="Study type (GLP or Non-GLP).")
    draft_maturity: str = Field(..., description="Draft maturity level (Early Draft, Near-Final, Final).")
    priority_notes: Optional[str] = Field(default=None, description="Optional notes to flag special considerations.")


class SessionSummary(BaseModel):
    """Minimal representation of a session for listing endpoints."""

    id: uuid.UUID
    study_name: Optional[str] = None
    study_type: Optional[str] = None
    draft_maturity: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


class SessionDetail(SessionSummary):
    """Detailed representation of a session including documents."""

    documents: List['DocumentResponse'] = []  # forward reference

    class Config:
        orm_mode = True


# Avoid circular import by importing DocumentResponse at module end
from .document import DocumentResponse  # noqa: E402, F401
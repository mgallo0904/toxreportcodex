"""Pydantic models for clarification endpoints.

These schemas define the shape of clarification data exchanged
between the backend and frontend.  A clarification represents a
question raised by the AI model during Pass 2 that requires human
input.  Clients can fetch pending clarifications, submit answers or
dismiss questions via these models.
"""

from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClarificationBase(BaseModel):
    """Base fields shared by all clarification schemas."""

    id: str = Field(..., description="Clarification UUID")
    session_id: str = Field(..., description="Parent session UUID")
    chunk_id: Optional[str] = Field(None, description="Chunk UUID this clarification pertains to")
    question_text: str = Field(..., description="The question posed by the AI model")
    status: str = Field(..., description="Current status of the clarification ('pending', 'answered', 'dismissed')")
    answer_text: Optional[str] = Field(None, description="User's answer, if provided")
    answered_at: Optional[datetime.datetime] = Field(None, description="Timestamp when the clarification was answered/dismissed")
    created_at: datetime.datetime = Field(..., description="Timestamp when the clarification was created")


class ClarificationResponse(ClarificationBase):
    """Clarification data returned by the API.

    Additional fields are included for convenience such as the
    originating document name and page range.  These fields are
    assembled in the router from associated document and chunk
    models.
    """

    document_name: Optional[str] = Field(None, description="Original filename of the document containing the chunk")
    page_range: Optional[str] = Field(None, description="Page range corresponding to the chunk, e.g. '12-14'")

    class Config:
        orm_mode = True


class ClarificationAnswer(BaseModel):
    """Model for submitting an answer to a clarification."""

    answer_text: str = Field(..., description="Textual answer provided by the user")

    class Config:
        schema_extra = {
            "example": {
                "answer_text": "The missing data are provided in section 3.2."
            }
        }
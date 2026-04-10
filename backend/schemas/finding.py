"""Pydantic models for finding endpoints.

Findings are the primary outputs of Pass 2.  Each finding
captures an identified issue along with its classification,
recommendation, severity and source information.  Users may
confirm or reject each finding; confirmed findings will later
populate the fine‑tuning dataset.
"""

from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FindingBase(BaseModel):
    """Base fields shared by all finding schemas."""

    id: str = Field(..., description="Finding UUID")
    session_id: str = Field(..., description="Parent session UUID")
    chunk_id: Optional[str] = Field(None, description="Chunk UUID from which this finding originates")
    document_id: Optional[str] = Field(None, description="Document UUID associated with the finding")
    finding_label: Optional[str] = Field(None, description="Sequential label (F-XXX) assigned to the finding")
    page_section_table: Optional[str] = Field(None, description="Reference to the page, section or table where the issue appears")
    original_text: Optional[str] = Field(None, description="Quoted original text from the source document")
    category: Optional[str] = Field(None, description="Category of the issue (e.g. Major Deviation)")
    comment: Optional[str] = Field(None, description="Additional descriptive comment")
    recommendation: Optional[str] = Field(None, description="Recommended action or remediation")
    severity: Optional[str] = Field(None, description="Severity classification (Critical, Moderate or Minor)")
    source_reference: Optional[str] = Field(None, description="Citation or reference supporting the finding")
    confidence: str = Field(..., description="Confidence level assigned by the model (standard or low)")
    confirmed_correct: Optional[bool] = Field(None, description="User confirmation status: True if correct, False if incorrect, None if undecided")
    confirmed_at: Optional[datetime.datetime] = Field(None, description="Timestamp when the user confirmed or rejected this finding")
    is_seed: bool = Field(..., description="Whether this finding originated from seed data")
    created_at: datetime.datetime = Field(..., description="Timestamp when the finding was created")


class FindingResponse(FindingBase):
    """Finding data returned by the API.

    Includes additional convenience fields for the associated document name
    and page range to aid display in the UI.
    """

    document_name: Optional[str] = Field(None, description="Original filename of the document containing the finding")
    page_range: Optional[str] = Field(None, description="Page range corresponding to the chunk, e.g. '12-14'")

    class Config:
        orm_mode = True


class FindingUpdate(BaseModel):
    """Model for updating a finding.

    Users can optionally override category, comment, recommendation and
    severity before confirming.  This schema is used when submitting
    confirmation to ensure the updated fields are captured correctly.
    """

    category: Optional[str] = Field(None, description="Updated issue category")
    comment: Optional[str] = Field(None, description="Updated descriptive comment")
    recommendation: Optional[str] = Field(None, description="Updated recommendation")
    severity: Optional[str] = Field(None, description="Updated severity classification")
    confirm: bool = Field(..., description="Whether the finding is confirmed (True) or rejected (False)")

    class Config:
        schema_extra = {
            "example": {
                "category": "Major Deviation",
                "comment": "Dose calculation error exceeds allowed variance.",
                "recommendation": "Repeat the study with corrected dose preparation.",
                "severity": "Critical",
                "confirm": True
            }
        }
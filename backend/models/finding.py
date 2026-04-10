"""Finding model definition.

A Finding represents an issue identified during Pass 2 along with its
classification, recommendation and severity. Findings may be confirmed
or rejected by the user; confirmed findings may later be used for
fine‑tuning the model.
"""

from __future__ import annotations

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    finding_label = Column(String, nullable=True)
    page_section_table = Column(String, nullable=True)
    original_text = Column(String, nullable=True)
    category = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    recommendation = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    source_reference = Column(String, nullable=True)
    confidence = Column(String, nullable=False, default="standard")
    confirmed_correct = Column(Boolean, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    is_seed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="findings")
    chunk = relationship("Chunk", back_populates="findings")
    document = relationship("Document", back_populates="findings")

    __table_args__ = (
        # Define allowable severities and default values
        # Checks for category/severity enumerations are defined in migrations for portability
        {},
    )
"""Claim model definition.

Claims represent extracted numerical or textual facts identified during
Pass 1. They include doses, concentrations, counts and other parameters
along with their context within the source document.
"""

from __future__ import annotations

from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    parameter_type = Column(String, nullable=False)
    parameter_name = Column(String, nullable=True)
    value = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    context_sentence = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    chunk = relationship("Chunk", back_populates="claims")
    document = relationship("Document", back_populates="claims")
    session = relationship("Session", back_populates="claims")
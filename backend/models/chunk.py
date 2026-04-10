"""Chunk model definition.

Chunks represent segments of document text processed independently by the
AI system. Each chunk is associated with a document and a session and
stores metadata about its position within the source file and its
processing state for both Pass 1 and Pass 2.
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    text_content = Column(Text, nullable=True)
    token_estimate = Column(Integer, nullable=True)
    pass1_status = Column(String, nullable=False, default="pending")
    pass2_status = Column(String, nullable=False, default="pending")
    pass2_selected = Column(Boolean, nullable=False, default=False)
    pass2_auto_selected = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")
    session = relationship("Session", back_populates="chunks")
    sections = relationship("DocumentSection", back_populates="chunk", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="chunk", cascade="all, delete-orphan")
    conflicts_a = relationship(
        "Conflict",
        foreign_keys="Conflict.chunk_id_a",
        back_populates="chunk_a",
    )
    conflicts_b = relationship(
        "Conflict",
        foreign_keys="Conflict.chunk_id_b",
        back_populates="chunk_b",
    )
    findings = relationship("Finding", back_populates="chunk", cascade="all, delete-orphan")
    clarifications = relationship("Clarification", back_populates="chunk", cascade="all, delete-orphan")
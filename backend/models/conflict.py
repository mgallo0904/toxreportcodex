"""Conflict model definition.

Conflicts represent situations where two documents report different
values for the same parameter. Each conflict records the conflicting
values and references to the source documents and chunks so that the
reviewer can resolve them in Pass 2.
"""

from __future__ import annotations

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Conflict(Base):
    __tablename__ = "conflicts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    parameter_name = Column(String, nullable=False)
    value_a = Column(String, nullable=True)
    document_id_a = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    chunk_id_a = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=True)
    page_a = Column(Integer, nullable=True)
    value_b = Column(String, nullable=True)
    document_id_b = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    chunk_id_b = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=True)
    page_b = Column(Integer, nullable=True)
    resolved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="conflicts")
    document_a = relationship("Document", foreign_keys=[document_id_a], back_populates="conflicts_a")
    document_b = relationship("Document", foreign_keys=[document_id_b], back_populates="conflicts_b")
    chunk_a = relationship("Chunk", foreign_keys=[chunk_id_a], back_populates="conflicts_a")
    chunk_b = relationship("Chunk", foreign_keys=[chunk_id_b], back_populates="conflicts_b")
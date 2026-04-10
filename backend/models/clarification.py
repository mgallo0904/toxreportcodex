"""Clarification model definition.

Clarification questions are created during Pass 2 when the model
determines that additional information is required from the user. Each
clarification tracks its state and the associated answer if provided.
"""

from __future__ import annotations

from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Clarification(Base):
    __tablename__ = "clarifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=True)
    question_text = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")
    answer_text = Column(Text, nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="clarifications")
    chunk = relationship("Chunk", back_populates="clarifications")
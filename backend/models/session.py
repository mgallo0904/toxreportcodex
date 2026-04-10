"""Session model definition.

The `Session` table represents an individual review session. It captures
metadata about the study package, processing status and timing of the
two processing passes. All timestamps are timezone‑aware and foreign
keys cascade deletes to dependent tables.
"""

from __future__ import annotations

import uuid
from sqlalchemy import Column, String, Boolean, CheckConstraint, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    study_name = Column(String, nullable=True)
    study_type = Column(String, nullable=True)
    draft_maturity = Column(String, nullable=True)
    priority_notes = Column(String, nullable=True)
    status = Column(String, nullable=False, default="uploading")
    active_model_id = Column(UUID(as_uuid=True), ForeignKey("model_configs.id", ondelete="SET NULL"), nullable=True)
    pass1_started_at = Column(DateTime(timezone=True), nullable=True)
    pass1_completed_at = Column(DateTime(timezone=True), nullable=True)
    pass2_started_at = Column(DateTime(timezone=True), nullable=True)
    pass2_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="session", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="session", cascade="all, delete-orphan")
    conflicts = relationship("Conflict", back_populates="session", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="session", cascade="all, delete-orphan")
    clarifications = relationship("Clarification", back_populates="session", cascade="all, delete-orphan")
    finetune_jobs = relationship("FinetuneJob", back_populates="sessions")
    model_configs = relationship("ModelConfig", back_populates="sessions")

    __table_args__ = (
        CheckConstraint("study_type IN ('GLP','Non-GLP')", name="ck_sessions_study_type"),
        CheckConstraint(
            "draft_maturity IN ('Early Draft','Near-Final','Final')",
            name="ck_sessions_draft_maturity",
        ),
        CheckConstraint(
            "status IN ('uploading','roles_assigned','mapping','section_selection','reviewing','complete')",
            name="ck_sessions_status",
        ),
    )
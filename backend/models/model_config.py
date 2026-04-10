"""ModelConfig model definition.

Stores metadata about available language models and fine‑tuned adapters.
Exactly one model config may be active at a time; the active model is
used for new inference requests. Fine‑tuned models reference the
corresponding finetune job.
"""

from __future__ import annotations

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    display_name = Column(String, nullable=False)
    model_tag = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    is_fine_tuned = Column(Boolean, nullable=False, default=False)
    base_model = Column(String, nullable=True)
    finetune_job_id = Column(UUID(as_uuid=True), ForeignKey("finetune_jobs.id"), nullable=True)
    context_length = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    finetune_job = relationship("FinetuneJob", back_populates="model_configs")
    sessions = relationship("Session", back_populates="model_configs")
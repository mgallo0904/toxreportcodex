"""FinetuneJob model definition.

Represents a fine‑tuning job executed on Modal.com. Stores the
hyperparameters used, the sessions included in training, status and
paths to any resulting adapters.
"""

from __future__ import annotations

from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class FinetuneJob(Base):
    __tablename__ = "finetune_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    base_model = Column(String, nullable=False)
    # Human‑friendly name for the fine‑tuned model, provided when creating the job.
    display_name = Column(String, nullable=True)
    training_session_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    training_example_count = Column(Integer, nullable=True)
    lora_rank = Column(Integer, nullable=False, default=16)
    lora_alpha = Column(Integer, nullable=False, default=32)
    epochs = Column(Integer, nullable=False, default=3)
    adapter_path = Column(String, nullable=True)
    ollama_model_tag = Column(String, nullable=True)
    status = Column(String, nullable=False, default="queued")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    sessions = relationship("Session", back_populates="finetune_jobs")
    model_configs = relationship("ModelConfig", back_populates="finetune_job")
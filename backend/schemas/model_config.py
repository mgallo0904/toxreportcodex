"""Pydantic models for model configurations.

Model configs represent language models available to the system,
including base models and fine‑tuned adapters.  One model may be
active at any given time; inference requests target the active
model.
"""

from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelConfigResponse(BaseModel):
    """Representation of a model configuration."""

    id: str = Field(..., description="Model configuration UUID")
    display_name: str = Field(..., description="Name shown to users")
    model_tag: str = Field(..., description="Tag used to identify the model in inference service")
    provider: str = Field(..., description="Provider of the model (e.g. openai, ollama)")
    is_fine_tuned: bool = Field(..., description="Indicates if this model is a fine‑tuned adapter")
    base_model: Optional[str] = Field(None, description="Base model tag if this is a fine‑tuned adapter")
    finetune_job_id: Optional[str] = Field(None, description="Reference to the finetune job that produced this model")
    context_length: Optional[int] = Field(None, description="Model's maximum context length")
    is_active: bool = Field(..., description="Whether this model is currently active")
    created_at: datetime.datetime = Field(..., description="Creation timestamp")

    class Config:
        orm_mode = True

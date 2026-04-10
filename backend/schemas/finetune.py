"""Pydantic models for finetune jobs and requests.

These schemas define the shape of fine‑tuning job requests and
responses.  A fine‑tune job trains a new adapter based on one or
more sessions' datasets.  The job creation request allows
specification of LoRA hyperparameters as optional overrides.
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FinetuneJobResponse(BaseModel):
    """Representation of a fine‑tune job returned by the API."""

    id: str = Field(..., description="Job UUID")
    base_model: str = Field(..., description="Identifier of the base model used")
    display_name: Optional[str] = Field(None, description="Human‑friendly name for the resulting model")
    training_session_ids: Optional[List[str]] = Field(None, description="Sessions used for training")
    training_example_count: Optional[int] = Field(None, description="Number of training examples")
    lora_rank: int = Field(..., description="LoRA rank hyperparameter")
    lora_alpha: int = Field(..., description="LoRA alpha hyperparameter")
    epochs: int = Field(..., description="Number of training epochs")
    adapter_path: Optional[str] = Field(None, description="Path to the resulting adapter")
    ollama_model_tag: Optional[str] = Field(None, description="Tag used for the model in the inference service")
    status: str = Field(..., description="Job status (queued, running, complete, error)")
    error_message: Optional[str] = Field(None, description="Error details if the job failed")
    started_at: Optional[datetime.datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime.datetime] = Field(None, description="Job completion timestamp")
    created_at: datetime.datetime = Field(..., description="Creation timestamp")

    class Config:
        orm_mode = True


class FinetuneJobCreate(BaseModel):
    """Request model for starting a new fine‑tune job."""

    base_model: str = Field(..., description="Base model tag to fine‑tune")
    session_ids: List[str] = Field(..., description="Sessions to include in training dataset")
    display_name: str = Field(..., description="Human‑friendly name for the resulting model")
    lora_rank: Optional[int] = Field(None, description="Optional override for LoRA rank")
    lora_alpha: Optional[int] = Field(None, description="Optional override for LoRA alpha")
    epochs: Optional[int] = Field(None, description="Optional override for number of epochs")

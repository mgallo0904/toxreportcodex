"""API router for fine‑tune jobs and model configurations.

This router provides endpoints to create and monitor fine‑tune jobs
and to manage model configurations.  Creating a job will gather
datasets from the specified sessions, count training examples and
record the job in the database.  In this simplified implementation
the job is immediately marked as complete and a new model config
record is created.
"""

from __future__ import annotations

import datetime
import uuid
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session_factory
from ..models import (
    FinetuneJob as FinetuneJobModel,
    ModelConfig as ModelConfigModel,
    Session as SessionModel,
    Finding as FindingModel,
)
from ..schemas.finetune import FinetuneJobResponse, FinetuneJobCreate
from ..schemas.model_config import ModelConfigResponse
from ..services.finetune_service import (
    build_training_jsonl,
    simulate_modal_training,
)


router = APIRouter(prefix="/api", tags=["finetune"])


async def get_db() -> AsyncSession:
    if async_session_factory is None:
        raise HTTPException(status_code=500, detail="Database is not configured")
    async with async_session_factory() as session:
        yield session


@router.post("/finetune/jobs", response_model=FinetuneJobResponse)
async def create_finetune_job(job: FinetuneJobCreate, db: AsyncSession = Depends(get_db)) -> FinetuneJobResponse:
    """Create a new fine‑tuning job.

    This endpoint prepares a dataset from the specified sessions,
    writes it to a JSONL file, and simulates submission of a QLoRA
    training job.  The job record is created with a status of
    ``running``.  Upon completion of the simulated training, the job
    status is updated to ``complete`` and the adapter path and
    model tag are recorded.  Model registration is handled by a
    separate ``load`` endpoint.
    """
    if not job.session_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one session must be specified")
    # Count training examples across sessions
    example_count = 0
    for sess_id in job.session_ids:
        res = await db.execute(
            select(FindingModel).where(
                FindingModel.session_id == sess_id,
                FindingModel.confirmed_correct.is_(True),
            )
        )
        example_count += len(res.scalars().all())
    if example_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No confirmed findings available for the selected sessions")
    # Create job record with initial status
    # Create a new job record, preserving the display name provided by the client.
    new_job = FinetuneJobModel(
        base_model=job.base_model,
        display_name=job.display_name,
        training_session_ids=job.session_ids,
        training_example_count=example_count,
        lora_rank=job.lora_rank or 16,
        lora_alpha=job.lora_alpha or 32,
        epochs=job.epochs or 3,
        status='running',
        started_at=datetime.datetime.utcnow(),
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)
    # Build JSONL file
    try:
        jsonl_path = await build_training_jsonl(db, new_job.training_session_ids, str(new_job.id))
        # Simulate training via Modal
        adapter_path, model_tag = await simulate_modal_training(new_job, jsonl_path)
        # Update job to complete
        new_job.status = 'complete'
        new_job.adapter_path = adapter_path
        new_job.ollama_model_tag = model_tag
        new_job.completed_at = datetime.datetime.utcnow()
        await db.commit()
        await db.refresh(new_job)
    except Exception as exc:
        new_job.status = 'error'
        new_job.error_message = str(exc)
        await db.commit()
    return FinetuneJobResponse(
        id=str(new_job.id),
        base_model=new_job.base_model,
        display_name=new_job.display_name,
        training_session_ids=new_job.training_session_ids,
        training_example_count=new_job.training_example_count,
        lora_rank=new_job.lora_rank,
        lora_alpha=new_job.lora_alpha,
        epochs=new_job.epochs,
        adapter_path=new_job.adapter_path,
        ollama_model_tag=new_job.ollama_model_tag,
        status=new_job.status,
        error_message=new_job.error_message,
        started_at=new_job.started_at,
        completed_at=new_job.completed_at,
        created_at=new_job.created_at,
    )


@router.get("/finetune/jobs", response_model=List[FinetuneJobResponse])
async def list_finetune_jobs(db: AsyncSession = Depends(get_db)) -> List[FinetuneJobResponse]:
    """List all fine‑tune jobs in the system."""
    result = await db.execute(select(FinetuneJobModel))
    jobs = result.scalars().all()
    responses: List[FinetuneJobResponse] = []
    for j in jobs:
        responses.append(
            FinetuneJobResponse(
                id=str(j.id),
                base_model=j.base_model,
                display_name=j.display_name,
                training_session_ids=j.training_session_ids,
                training_example_count=j.training_example_count,
                lora_rank=j.lora_rank,
                lora_alpha=j.lora_alpha,
                epochs=j.epochs,
                adapter_path=j.adapter_path,
                ollama_model_tag=j.ollama_model_tag,
                status=j.status,
                error_message=j.error_message,
                started_at=j.started_at,
                completed_at=j.completed_at,
                created_at=j.created_at,
            )
        )
    return responses


@router.get("/finetune/jobs/{job_id}", response_model=FinetuneJobResponse)
async def get_finetune_job(job_id: str, db: AsyncSession = Depends(get_db)) -> FinetuneJobResponse:
    """Retrieve details about a specific fine‑tune job."""
    result = await db.execute(
        select(FinetuneJobModel).where(FinetuneJobModel.id == job_id)
    )
    job: FinetuneJobModel | None = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finetune job not found")
    return FinetuneJobResponse(
        id=str(job.id),
        base_model=job.base_model,
        display_name=job.display_name,
        training_session_ids=job.training_session_ids,
        training_example_count=job.training_example_count,
        lora_rank=job.lora_rank,
        lora_alpha=job.lora_alpha,
        epochs=job.epochs,
        adapter_path=job.adapter_path,
        ollama_model_tag=job.ollama_model_tag,
        status=job.status,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


@router.get("/finetune/training-data")
async def get_training_data(
    session_ids: List[str] | None = Query(None, description="List of session IDs to include in training"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return a summary of available training data for fine‑tuning.

    If no session IDs are provided, all sessions containing at least
    one confirmed finding will be included.  The summary includes
    total training example count, counts by severity and a list of
    sessions with their confirmed finding counts.
    """
    # Determine which sessions to include
    included_sessions: List[str] = []
    if session_ids:
        included_sessions = list(session_ids)
    else:
        # Find distinct session IDs that have confirmed findings
        result = await db.execute(
            select(FindingModel.session_id).where(FindingModel.confirmed_correct.is_(True)).distinct()
        )
        included_sessions = [str(row[0]) for row in result.fetchall()]
    example_count = 0
    critical_count = 0
    moderate_count = 0
    minor_count = 0
    sessions_list: List[Dict[str, Any]] = []
    for sess_id in included_sessions:
        # Load session name
        res_sess = await db.execute(select(SessionModel).where(SessionModel.id == sess_id))
        sess = res_sess.scalar_one_or_none()
        if not sess:
            continue
        # Load confirmed findings for this session
        res_find = await db.execute(
            select(FindingModel).where(
                FindingModel.session_id == sess_id,
                FindingModel.confirmed_correct.is_(True),
            )
        )
        f_list = res_find.scalars().all()
        count = len(f_list)
        if count == 0:
            continue
        sessions_list.append({
            "id": str(sess_id),
            "study_name": sess.study_name,
            "confirmed_count": count,
        })
        example_count += count
        for f in f_list:
            if f.severity == 'Critical':
                critical_count += 1
            elif f.severity == 'Moderate':
                moderate_count += 1
            elif f.severity == 'Minor':
                minor_count += 1
    return {
        "example_count": example_count,
        "critical_count": critical_count,
        "moderate_count": moderate_count,
        "minor_count": minor_count,
        "sessions_included": sessions_list,
    }


@router.get("/model-configs", response_model=List[ModelConfigResponse])
async def list_model_configs(db: AsyncSession = Depends(get_db)) -> List[ModelConfigResponse]:
    """Retrieve all model configurations."""
    result = await db.execute(select(ModelConfigModel))
    configs = result.scalars().all()
    responses: List[ModelConfigResponse] = []
    for cfg in configs:
        responses.append(
            ModelConfigResponse(
                id=str(cfg.id),
                display_name=cfg.display_name,
                model_tag=cfg.model_tag,
                provider=cfg.provider,
                is_fine_tuned=cfg.is_fine_tuned,
                base_model=cfg.base_model,
                finetune_job_id=str(cfg.finetune_job_id) if cfg.finetune_job_id else None,
                context_length=cfg.context_length,
                is_active=cfg.is_active,
                created_at=cfg.created_at,
            )
        )
    return responses


@router.post("/model-configs/{model_id}/activate", response_model=ModelConfigResponse)
async def activate_model_config(model_id: str, db: AsyncSession = Depends(get_db)) -> ModelConfigResponse:
    """Activate the specified model configuration.

    Sets the `is_active` flag on the chosen model and clears it on
    all others.  Returns the activated model configuration.  If
    the specified model does not exist, a 404 error is raised.
    """
    result = await db.execute(
        select(ModelConfigModel).where(ModelConfigModel.id == model_id)
    )
    model: ModelConfigModel | None = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model configuration not found")
    # Deactivate all models
    await db.execute(ModelConfigModel.__table__.update().values(is_active=False))
    # Activate selected
    model.is_active = True
    await db.commit()
    await db.refresh(model)
    return ModelConfigResponse(
        id=str(model.id),
        display_name=model.display_name,
        model_tag=model.model_tag,
        provider=model.provider,
        is_fine_tuned=model.is_fine_tuned,
        base_model=model.base_model,
        finetune_job_id=str(model.finetune_job_id) if model.finetune_job_id else None,
        context_length=model.context_length,
        is_active=model.is_active,
        created_at=model.created_at,
    )


@router.post("/finetune/jobs/{job_id}/load", response_model=ModelConfigResponse)
async def load_finetune_adapter(job_id: str, db: AsyncSession = Depends(get_db)) -> ModelConfigResponse:
    """Register a completed fine‑tune job as a new model configuration.

    This endpoint checks that the specified job has completed and has
    an adapter available.  It then creates a ``model_config``
    referencing the job and returns the resulting configuration.  The
    new model is not activated by default; clients may activate it
    using the model activation endpoint.
    """
    # Fetch job
    result = await db.execute(select(FinetuneJobModel).where(FinetuneJobModel.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finetune job not found")
    if job.status != 'complete' or not job.adapter_path or not job.ollama_model_tag:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Finetune job is not ready to load")
    # Create model configuration
    # Determine display name: prefer job.display_name if provided; otherwise fall back to base model
    model_display_name: str
    if job.display_name:
        model_display_name = job.display_name
    else:
        model_display_name = f"{job.base_model} (FT) {job_id[:8]}"
    new_config = ModelConfigModel(
        display_name=model_display_name,
        model_tag=job.ollama_model_tag,
        provider='ollama',
        is_fine_tuned=True,
        base_model=job.base_model,
        finetune_job_id=job.id,
        context_length=4096,
        is_active=False,
    )
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    return ModelConfigResponse(
        id=str(new_config.id),
        display_name=new_config.display_name,
        model_tag=new_config.model_tag,
        provider=new_config.provider,
        is_fine_tuned=new_config.is_fine_tuned,
        base_model=new_config.base_model,
        finetune_job_id=str(new_config.finetune_job_id) if new_config.finetune_job_id else None,
        context_length=new_config.context_length,
        is_active=new_config.is_active,
        created_at=new_config.created_at,
    )
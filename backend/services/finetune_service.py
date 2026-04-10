"""Fine-tuning service.

This module encapsulates helper functions to build training datasets
for fine‑tuning and to simulate submission of jobs to a remote
service (Modal.com).  In a production setting, these functions
would export JSONL files and invoke the Modal client to execute a
QLoRA training script.  Here we stub out the Modal integration and
instead write the dataset and adapter files to the local storage
path, immediately marking jobs as complete.
"""

from __future__ import annotations

import json
import os
import datetime
from pathlib import Path
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import FinetuneJob as FinetuneJobModel
from .dataset_builder import export_session_dataset


async def build_training_jsonl(
    db: AsyncSession, session_ids: List[str], job_id: str
) -> str:
    """Export a JSONL training file for the specified sessions.

    This function iterates over the confirmed findings in each
    session using the dataset builder service.  Each finding is
    converted to a training example consisting of a fixed
    instruction, the chunk text as input and a JSON string
    containing the finding inside an array and an empty list of
    clarifications as output.  The examples are concatenated into
    a single JSONL file stored under
    ``{storage_path}/finetune/{job_id}/training.jsonl``.

    Parameters
    ----------
    db: AsyncSession
        Active database session.
    session_ids: List[str]
        Sessions to include in the training dataset.
    job_id: str
        Unique identifier for the fine‑tune job (used for output path).

    Returns
    -------
    str
        Absolute filesystem path to the generated JSONL file.
    """
    settings = get_settings()
    base_dir = Path(getattr(settings, "storage_path", "/var/data")).joinpath("finetune", str(job_id))
    base_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = base_dir.joinpath("training.jsonl")
    instruction_text = (
        "You are a senior nonclinical toxicology consultant reviewing a study report. "
        "Identify findings according to GLP compliance standards, internal consistency, "
        "scientific rigor, and regulatory requirements."
    )
    with jsonl_path.open("w", encoding="utf-8") as f:
        for sess_id in session_ids:
            # Export confirmed findings for this session
            dataset = await export_session_dataset(db, sess_id)
            for record in dataset:
                # Use chunk_text if available, otherwise original_text as the input
                input_text = record.get("chunk_text") or record.get("original_text") or ""
                # Build minimal finding object for training output
                finding_obj = {
                    "finding_id": record.get("finding_id"),
                    "finding_label": record.get("finding_label"),
                    "category": record.get("category"),
                    "comment": record.get("comment"),
                    "recommendation": record.get("recommendation"),
                    "severity": record.get("severity"),
                    "source_reference": record.get("source_reference"),
                    "original_text": record.get("original_text"),
                    "document_name": record.get("document_name"),
                    "page_range": record.get("page_range"),
                }
                output_payload = {
                    "findings": [finding_obj],
                    "clarifications": [],
                }
                example = {
                    "instruction": instruction_text,
                    "input": input_text,
                    # Dump the output payload as a JSON string; ensure ASCII characters are preserved
                    "output": json.dumps(output_payload, ensure_ascii=False),
                }
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
    return str(jsonl_path)


async def simulate_modal_training(
    job: FinetuneJobModel, jsonl_path: str
) -> Tuple[str, str]:
    """Simulate submission of a fine‑tune job to Modal and return adapter info.

    This stub function pretends to perform a training run on the
    provided JSONL file.  It writes an empty file representing the
    LoRA adapter to the `adapters/{job_id}` directory within the
    configured storage path.  It then returns both the adapter
    filesystem path and a mock model tag.

    Parameters
    ----------
    job: FinetuneJobModel
        The job record being processed.
    jsonl_path: str
        Absolute path to the training JSONL file.

    Returns
    -------
    Tuple[str, str]
        A tuple (adapter_path, model_tag) where adapter_path is the
        absolute path to the saved adapter file and model_tag is a
        unique identifier suitable for registering the model in the
        inference service.
    """
    settings = get_settings()
    adapters_dir = Path(getattr(settings, "storage_path", "/var/data")).joinpath("adapters", str(job.id))
    adapters_dir.mkdir(parents=True, exist_ok=True)
    adapter_path = adapters_dir.joinpath("adapter.bin")
    # Write a placeholder file to represent the adapter
    with adapter_path.open("wb") as fh:
        fh.write(b"FAKEADAPTER")
    # Generate a mock model tag using the job ID
    model_tag = f"ft-{job.id}"
    return str(adapter_path), model_tag
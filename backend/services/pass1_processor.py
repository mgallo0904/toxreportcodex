"""Pass 1 processor service.

This module implements the structural mapping phase of the review
pipeline.  When a session transitions from role assignment to
mapping, Pass 1 iterates through all document chunks, sends each to
the inference service with the Pass 1 system prompt, parses the
resulting JSON and writes `DocumentSection` and `Claim` records to
the database.  After all chunks are processed, it runs conflict
detection and updates the session status to `section_selection`.

Progress information is stored in a module‑level dictionary
`PASS1_PROGRESS` keyed by session ID.  The `GET /pass1/status`
endpoint reads from this structure to provide live progress updates.

Note: This code relies on SQLAlchemy and httpx which may not be
available in this environment.  It should be executed in an
environment where the full dependency stack is installed.
"""

from __future__ import annotations

import asyncio
import json
import datetime
from typing import Dict, Any, List

from sqlalchemy import select

from ..config import get_settings
from ..database import async_session_factory
from ..models import (
    Session as SessionModel,
    Document as DocumentModel,
    Chunk as ChunkModel,
    DocumentSection,
    Claim,
)
from .inference_client import InferenceClient, InferenceError
from .conflict_detector import detect_conflicts


# Shared progress dictionary.  Each entry is of the form:
# {
#   "status": str,
#   "total_chunks": int,
#   "completed_chunks": int,
#   "current_document": str | None,
#   "current_pages": str | None,
#   "log": list[dict],
#   "conflicts_found": int
# }
PASS1_PROGRESS: Dict[str, Dict[str, Any]] = {}


async def run_pass1(session_id: str) -> None:
    """Run the Pass 1 structural mapping job for a session.

    This coroutine is intended to be scheduled as a background task.  It
    uses an independent database session to avoid interfering with the
    request context.  Progress is recorded in the `PASS1_PROGRESS`
    dictionary for consumption by the `/pass1/status` endpoint.

    Parameters
    ----------
    session_id: str
        The UUID of the session to process.
    """
    # Lazily import async_session_factory in case SQLAlchemy is not installed
    if async_session_factory is None:
        # Without a database session, nothing can be processed.  Record error status.
        PASS1_PROGRESS[str(session_id)] = {
            "status": "error",
            "total_chunks": 0,
            "completed_chunks": 0,
            "current_document": None,
            "current_pages": None,
            "log": [],
            "conflicts_found": 0,
        }
        return
    settings = get_settings()
    # Determine active model tag
    model_tag = settings.default_model_tag
    # We must query the database to find the active model tag.  We'll
    # default to the configured default if none is active.
    async with async_session_factory() as db:
        try:
            from ..models import ModelConfig
            result_model = await db.execute(select(ModelConfig).where(ModelConfig.is_active.is_(True)))
            active_model = result_model.scalar_one_or_none()
            if active_model is not None:
                model_tag = active_model.model_tag
        except Exception:
            # If ModelConfig table doesn't exist or cannot be queried, fall back to default
            pass
    # Create inference client
    client = InferenceClient(settings.inference_base_url, settings.inference_api_key, model_tag)
    # Read system prompt from file.  Always resolve relative to the prompts
    # directory in the backend package.  This avoids reliance on settings
    # attributes that may not exist.
    import os
    prompt_file = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'pass1_mapper.txt')
    with open(os.path.abspath(prompt_file), 'r', encoding='utf-8') as f:
        system_prompt = f.read()
    # Initialise progress entry
    PASS1_PROGRESS[str(session_id)] = {
        "status": "mapping",
        "total_chunks": 0,
        "completed_chunks": 0,
        "current_document": None,
        "current_pages": None,
        "log": [],
        "conflicts_found": 0,
    }
    # Acquire DB session for processing
    async with async_session_factory() as db:
        # Fetch session and update status/start timestamp
        result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        session_obj: SessionModel | None = result.scalar_one_or_none()
        if session_obj is None:
            PASS1_PROGRESS[str(session_id)]["status"] = "error"
            return
        session_obj.status = "mapping"
        session_obj.pass1_started_at = datetime.datetime.utcnow()
        await db.commit()
        # Count total chunks
        result_total = await db.execute(select(ChunkModel).where(ChunkModel.session_id == session_id))
        all_chunks: List[ChunkModel] = list(result_total.scalars().all())
        total_chunks = len(all_chunks)
        PASS1_PROGRESS[str(session_id)]["total_chunks"] = total_chunks
        completed = 0
        # Order chunks by document order then chunk_index
        # We'll fetch documents and iterate accordingly
        docs_result = await db.execute(select(DocumentModel).where(DocumentModel.session_id == session_id))
        documents = docs_result.scalars().all()
        # Sort by created_at to ensure upload order
        documents.sort(key=lambda d: d.created_at)
        for doc in documents:
            doc_chunks = [c for c in all_chunks if c.document_id == doc.id]
            # Sort by chunk_index
            doc_chunks.sort(key=lambda c: c.chunk_index)
            for chunk in doc_chunks:
                # Update progress
                PASS1_PROGRESS[str(session_id)]["current_document"] = doc.original_filename
                if chunk.page_start is not None and chunk.page_end is not None:
                    PASS1_PROGRESS[str(session_id)]["current_pages"] = f"{chunk.page_start}-{chunk.page_end}"
                elif chunk.page_start is not None:
                    PASS1_PROGRESS[str(session_id)]["current_pages"] = str(chunk.page_start)
                else:
                    PASS1_PROGRESS[str(session_id)]["current_pages"] = None
                # Set chunk status to processing
                chunk.pass1_status = "processing"
                await db.commit()
                # Call inference client with retry
                response_text: str | None = None
                retry_attempts = 2
                error_encountered = None
                for attempt in range(retry_attempts):
                    try:
                        response_text = await client.complete(system_prompt, chunk.text_content or "", max_tokens=4000, temperature=0.0)
                        break
                    except InferenceError as e:
                        error_encountered = e
                        if attempt < retry_attempts - 1:
                            await asyncio.sleep(5)
                if response_text is None:
                    # Mark chunk as error and log
                    chunk.pass1_status = "error"
                    await db.commit()
                    PASS1_PROGRESS[str(session_id)]["log"].append({
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "document": doc.original_filename,
                        "pages": PASS1_PROGRESS[str(session_id)]["current_pages"],
                        "status": "error",
                        "message": str(error_encountered),
                    })
                    continue
                # Parse JSON
                try:
                    result_json = json.loads(response_text)
                except Exception as exc:
                    # Second retry if invalid JSON
                    # We already attempted inference twice; treat as error
                    chunk.pass1_status = "error"
                    await db.commit()
                    PASS1_PROGRESS[str(session_id)]["log"].append({
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "document": doc.original_filename,
                        "pages": PASS1_PROGRESS[str(session_id)]["current_pages"],
                        "status": "error",
                        "message": f"Invalid JSON: {exc}",
                    })
                    continue
                # Extract sections
                sections = result_json.get("sections", []) or []
                # Hierarchy tracking
                last_section_by_level: Dict[int, DocumentSection] = {}
                for sec in sections:
                    try:
                        header = sec.get("header")
                        page = sec.get("page")
                        level = sec.get("level") or 1
                        parent_id = None
                        if isinstance(level, int) and level > 1:
                            parent_section = last_section_by_level.get(level - 1)
                            if parent_section:
                                parent_id = parent_section.id
                        section_obj = DocumentSection(
                            chunk_id=chunk.id,
                            document_id=doc.id,
                            session_id=session_id,
                            header_text=header or "",
                            page_number=page if page is not None else None,
                            section_level=level if isinstance(level, int) else 1,
                            parent_section_id=parent_id,
                        )
                        db.add(section_obj)
                        # Store for hierarchy building
                        if isinstance(level, int):
                            last_section_by_level[level] = section_obj
                    except Exception:
                        # Skip invalid section record
                        continue
                # Extract abbreviations as claims
                for abbr in result_json.get("abbreviations", []) or []:
                    term = abbr.get("term")
                    definition = abbr.get("definition")
                    page = abbr.get("page")
                    claim = Claim(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        session_id=session_id,
                        parameter_type="abbreviation",
                        parameter_name=term,
                        value=definition,
                        unit=None,
                        context_sentence=None,
                        page_number=page if page is not None else None,
                    )
                    db.add(claim)
                # Extract numerical claims
                for cl in result_json.get("numerical_claims", []) or []:
                    parameter_type = cl.get("parameter_type")
                    parameter_name = cl.get("parameter_name")
                    value = cl.get("value")
                    unit = cl.get("unit")
                    context = cl.get("context")
                    page = cl.get("page")
                    claim = Claim(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        session_id=session_id,
                        parameter_type=parameter_type,
                        parameter_name=parameter_name,
                        value=value,
                        unit=unit,
                        context_sentence=context,
                        page_number=page if page is not None else None,
                    )
                    db.add(claim)
                # Extract conclusions
                for conc in result_json.get("conclusions", []) or []:
                    text = conc.get("text")
                    page = conc.get("page")
                    claim = Claim(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        session_id=session_id,
                        parameter_type="conclusion",
                        parameter_name=None,
                        value=text,
                        unit=None,
                        context_sentence=None,
                        page_number=page if page is not None else None,
                    )
                    db.add(claim)
                # Extract methods
                for m in result_json.get("methods", []) or []:
                    label = m.get("label")
                    page = m.get("page")
                    claim = Claim(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        session_id=session_id,
                        parameter_type="method",
                        parameter_name=None,
                        value=label,
                        unit=None,
                        context_sentence=None,
                        page_number=page if page is not None else None,
                    )
                    db.add(claim)
                # Mark chunk complete
                chunk.pass1_status = "complete"
                completed += 1
                PASS1_PROGRESS[str(session_id)]["completed_chunks"] = completed
                # Log entry
                PASS1_PROGRESS[str(session_id)]["log"].append({
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "document": doc.original_filename,
                    "pages": PASS1_PROGRESS[str(session_id)]["current_pages"],
                    "status": "complete",
                })
                # Persist changes after each chunk to avoid large transaction
                await db.commit()
        # All chunks processed
        # Run conflict detector to flag conflicting values.  This returns
        # the number of conflicts created.
        conflict_count = await detect_conflicts(session_id, db)
        PASS1_PROGRESS[str(session_id)]["conflicts_found"] = conflict_count
        # Compute counts of indexed sections and extracted claims for the
        # summary.  These counts are stored in the progress dict so that
        # the UI can display them when Pass 1 completes.  If the tables
        # are unavailable (e.g. SQLAlchemy not installed), counts will
        # remain 0.
        try:
            from ..models import DocumentSection as SectionModel, Claim as ClaimModel
            result_sections = await db.execute(select(SectionModel).where(SectionModel.session_id == session_id))
            sections_count = len(result_sections.scalars().all())
            result_claims = await db.execute(select(ClaimModel).where(ClaimModel.session_id == session_id))
            claims_count = len(result_claims.scalars().all())
        except Exception:
            sections_count = 0
            claims_count = 0
        PASS1_PROGRESS[str(session_id)]["sections_indexed"] = sections_count
        PASS1_PROGRESS[str(session_id)]["claims_extracted"] = claims_count
        # Update session status to section_selection
        result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        session_obj = result.scalar_one_or_none()
        if session_obj is not None:
            session_obj.status = "section_selection"
            session_obj.pass1_completed_at = datetime.datetime.utcnow()
            await db.commit()
        PASS1_PROGRESS[str(session_id)]["status"] = "section_selection"

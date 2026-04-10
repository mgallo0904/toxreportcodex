"""Pass 2 processor service.

This module implements the deep review phase of the toxicology review
pipeline.  Pass 2 runs only on chunks that have been selected by the
user (or automatically due to conflicts).  For each selected chunk, it
constructs a fully contextual prompt using `prompt_builder`, calls
the inference service, parses the returned findings and
clarifications, writes results to the database, and handles the
clarification pause/resume cycle.  Progress is tracked in the
module‑level `PASS2_PROGRESS` dictionary for consumption by the
`/pass2/status` endpoint.

Note: As with other services, this module depends on SQLAlchemy and
httpx.  In environments where these packages are unavailable, the
functions defined here will not run and should be considered
non‑functional stubs.
"""

from __future__ import annotations

import asyncio
import datetime
import json
from typing import Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import async_session_factory
from ..models import (
    Session as SessionModel,
    Chunk as ChunkModel,
    Document as DocumentModel,
    Finding as FindingModel,
    Clarification as ClarificationModel,
    ModelConfig,
)
from ..services.prompt_builder import build_pass2_prompt
from ..services.inference_client import InferenceClient, InferenceError


# Shared progress dictionary.  Each entry tracks the current status of
# a Pass 2 job keyed by session ID.  The structure mirrors that used
# by Pass 1 but includes additional fields for clarifications and
# finding counts.
PASS2_PROGRESS: Dict[str, Dict[str, Any]] = {}


async def _get_active_model_tag(db: AsyncSession, default_tag: str) -> str:
    """Retrieve the active model tag from the database or return the default.

    Parameters
    ----------
    db: AsyncSession
        Active database session.
    default_tag: str
        Fallback model tag if none is active.

    Returns
    -------
    str
        The active model tag.
    """
    try:
        result_model = await db.execute(select(ModelConfig).where(ModelConfig.is_active.is_(True)))
        active_model = result_model.scalar_one_or_none()
        if active_model is not None:
            return active_model.model_tag
    except Exception:
        # Table may not exist or query failed
        pass
    return default_tag


async def run_pass2(session_id: str) -> None:
    """Run the Pass 2 deep review job for a session.

    This coroutine is intended to be scheduled as a background task by
    the API layer.  It operates independently of any request context.
    It updates session status, processes selected chunks, handles
    clarifications, writes findings, and records progress in
    `PASS2_PROGRESS`.

    Parameters
    ----------
    session_id: str
        The UUID of the session to process.
    """
    # If database session factory is unavailable (e.g. missing SQLAlchemy), record error
    if async_session_factory is None:
        PASS2_PROGRESS[str(session_id)] = {
            "status": "error",
            "total_selected": 0,
            "completed_selected": 0,
            "current_document": None,
            "current_pages": None,
            "pending_clarifications": 0,
            "log": [],
            "critical_count": 0,
            "moderate_count": 0,
            "minor_count": 0,
        }
        return
    settings = get_settings()
    # Open database session
    async with async_session_factory() as db:
        # Fetch session
        result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        session_obj: SessionModel | None = result.scalar_one_or_none()
        if session_obj is None:
            # Session missing: record error
            PASS2_PROGRESS[str(session_id)] = {
                "status": "error",
                "total_selected": 0,
                "completed_selected": 0,
                "current_document": None,
                "current_pages": None,
                "pending_clarifications": 0,
                "log": [],
                "critical_count": 0,
                "moderate_count": 0,
                "minor_count": 0,
            }
            return
        # Update session status to reviewing and record start time
        session_obj.status = "reviewing"
        session_obj.pass2_started_at = datetime.datetime.utcnow()
        await db.commit()
        # Determine active model tag
        default_tag = settings.default_model_tag
        model_tag = await _get_active_model_tag(db, default_tag)
        # Create inference client
        client = InferenceClient(settings.inference_base_url, settings.inference_api_key, model_tag)
        # Fetch selected chunks (only those flagged pass2_selected)
        result_chunks = await db.execute(
            select(ChunkModel).where(
                ChunkModel.session_id == session_id,
                ChunkModel.pass2_selected.is_(True),
            )
        )
        selected_chunks = result_chunks.scalars().all()
        # Sort selected chunks by document creation time then chunk index to maintain
        # deterministic ordering
        # Build a mapping from document_id to created_at for sorting
        result_docs = await db.execute(
            select(DocumentModel.id, DocumentModel.created_at).where(DocumentModel.session_id == session_id)
        )
        doc_dates = {row[0]: row[1] for row in result_docs}
        selected_chunks.sort(key=lambda c: (doc_dates.get(c.document_id), c.chunk_index))
        total_selected = len(selected_chunks)
        # Initialise progress
        progress_key = str(session_id)
        PASS2_PROGRESS[progress_key] = {
            "status": "reviewing",
            "total_selected": total_selected,
            "completed_selected": 0,
            "current_document": None,
            "current_pages": None,
            "pending_clarifications": 0,
            "log": [],
            "critical_count": 0,
            "moderate_count": 0,
            "minor_count": 0,
        }
        completed = 0
        # Determine next finding label index by scanning existing finding labels
        next_label_index = 1
        try:
            result_findings = await db.execute(
                select(FindingModel.finding_label).where(FindingModel.session_id == session_id)
            )
            existing_labels = result_findings.scalars().all()
            max_index = 0
            for label in existing_labels:
                if label and label.startswith('F-'):
                    try:
                        idx = int(label.split('-')[1])
                        if idx > max_index:
                            max_index = idx
                    except (ValueError, IndexError):
                        continue
            next_label_index = max_index + 1
        except Exception:
            # ignore errors determining next label
            next_label_index = 1
        # Process each selected chunk
        for chunk in selected_chunks:
            # Update progress current document/page
            # Fetch document for display
            result_doc = await db.execute(select(DocumentModel).where(DocumentModel.id == chunk.document_id))
            doc_obj = result_doc.scalar_one_or_none()
            doc_name = doc_obj.original_filename if doc_obj else ''
            PASS2_PROGRESS[progress_key]["current_document"] = doc_name
            # Build page range string
            if chunk.page_start is not None and chunk.page_end is not None:
                page_range = f"{chunk.page_start}-{chunk.page_end}"
            elif chunk.page_start is not None:
                page_range = str(chunk.page_start)
            else:
                page_range = ''
            PASS2_PROGRESS[progress_key]["current_pages"] = page_range
            # Mark chunk as processing
            chunk.pass2_status = "processing"
            await db.commit()
            # Build prompt
            try:
                system_prompt, user_content = await build_pass2_prompt(db, session_obj, chunk)
            except Exception as exc:
                # Record error and skip this chunk
                chunk.pass2_status = "error"
                await db.commit()
                PASS2_PROGRESS[progress_key]["log"].append({
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "document": doc_name,
                    "pages": page_range,
                    "status": "error",
                    "message": f"Prompt build failed: {exc}",
                })
                continue
            # Call inference with retries
            response_text: str | None = None
            error_encountered = None
            for attempt in range(2):
                try:
                    response_text = await client.complete(system_prompt, user_content, max_tokens=8000, temperature=0.0)
                    break
                except InferenceError as ie:
                    error_encountered = ie
                    if attempt < 1:
                        await asyncio.sleep(5)
            if response_text is None:
                # Mark error and continue
                chunk.pass2_status = "error"
                await db.commit()
                PASS2_PROGRESS[progress_key]["log"].append({
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "document": doc_name,
                    "pages": page_range,
                    "status": "error",
                    "message": str(error_encountered),
                })
                continue
            # Parse JSON
            try:
                result_json = json.loads(response_text)
            except Exception as exc:
                # Invalid JSON
                chunk.pass2_status = "error"
                await db.commit()
                PASS2_PROGRESS[progress_key]["log"].append({
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "document": doc_name,
                    "pages": page_range,
                    "status": "error",
                    "message": f"Invalid JSON: {exc}",
                })
                continue
            findings_data = result_json.get("findings", []) or []
            clarif_data = result_json.get("clarifications", []) or []
            # Insert findings
            critical_count = 0
            moderate_count = 0
            minor_count = 0
            for finding in findings_data:
                try:
                    label = f"F-{next_label_index:03d}"
                    next_label_index += 1
                    new_finding = FindingModel(
                        session_id=session_obj.id,
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        finding_label=label,
                        page_section_table=finding.get('page_section_table'),
                        original_text=finding.get('original_text'),
                        category=finding.get('category'),
                        comment=finding.get('comment'),
                        recommendation=finding.get('recommendation'),
                        severity=finding.get('severity'),
                        source_reference=finding.get('source_reference'),
                        confidence='standard',
                    )
                    db.add(new_finding)
                    # Count severity for progress
                    sev = (finding.get('severity') or '').lower()
                    if sev == 'critical':
                        critical_count += 1
                    elif sev == 'moderate':
                        moderate_count += 1
                    elif sev == 'minor':
                        minor_count += 1
                except Exception:
                    # Skip invalid finding entries
                    continue
            # Create clarifications
            clarif_ids: List[str] = []
            for clarif in clarif_data:
                q = clarif.get('question')
                if not q:
                    continue
                clarification = ClarificationModel(
                    session_id=session_obj.id,
                    chunk_id=chunk.id,
                    question_text=q,
                    status='pending',
                )
                db.add(clarification)
            # Persist findings and clarifications
            await db.commit()
            # Update progress counts
            PASS2_PROGRESS[progress_key]["critical_count"] += critical_count
            PASS2_PROGRESS[progress_key]["moderate_count"] += moderate_count
            PASS2_PROGRESS[progress_key]["minor_count"] += minor_count
            # Refresh clarifications list for this chunk
            # Wait for clarifications to be resolved if any pending
            if clarif_data:
                # Determine clarifications for this chunk
                while True:
                    # Query pending clarifications for this chunk
                    result_pending = await db.execute(
                        select(ClarificationModel).where(
                            ClarificationModel.session_id == session_obj.id,
                            ClarificationModel.chunk_id == chunk.id,
                            ClarificationModel.status == 'pending',
                        )
                    )
                    pending_clarifs = result_pending.scalars().all()
                    pending_count = len(pending_clarifs)
                    PASS2_PROGRESS[progress_key]["pending_clarifications"] = pending_count
                    if pending_count == 0:
                        break
                    # Sleep before checking again
                    await asyncio.sleep(5)
                # Clarifications resolved; mark findings as low confidence if any were dismissed
                result_dismissed = await db.execute(
                    select(ClarificationModel).where(
                        ClarificationModel.session_id == session_obj.id,
                        ClarificationModel.chunk_id == chunk.id,
                        ClarificationModel.status == 'dismissed',
                    )
                )
                dismissed = result_dismissed.scalars().all()
                if dismissed:
                    # Update all findings in this chunk: set confidence to low
                    await db.execute(
                        FindingModel.__table__.update()
                        .where(
                            FindingModel.session_id == session_obj.id,
                            FindingModel.chunk_id == chunk.id,
                        )
                        .values(confidence='low')
                    )
                    await db.commit()
            # Mark chunk complete
            chunk.pass2_status = 'complete'
            await db.commit()
            completed += 1
            PASS2_PROGRESS[progress_key]["completed_selected"] = completed
            # Log entry
            PASS2_PROGRESS[progress_key]["log"].append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "document": doc_name,
                "pages": page_range,
                "status": "complete",
            })
        # All selected chunks processed
        # Compute severity counts from DB if needed (already accumulated during loop)
        # Update session status and completion timestamp
        result_session = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        sess = result_session.scalar_one_or_none()
        if sess is not None:
            sess.status = 'complete'
            sess.pass2_completed_at = datetime.datetime.utcnow()
            await db.commit()
        # Compute final pending clarifications count (should be 0)
        result_pending_final = await db.execute(
            select(ClarificationModel).where(
                ClarificationModel.session_id == session_id,
                ClarificationModel.status == 'pending',
            )
        )
        final_pending = len(result_pending_final.scalars().all())
        PASS2_PROGRESS[progress_key]["pending_clarifications"] = final_pending
        # Set progress status to complete
        PASS2_PROGRESS[progress_key]["status"] = 'complete'
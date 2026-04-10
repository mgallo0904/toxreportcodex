"""API router for the Pass 2 deep review phase.

This router exposes endpoints to initiate Pass 2 on a session and
monitor its progress.  Starting Pass 2 requires the client to
specify which chunks were selected during the section selection
stage; the backend marks these chunks accordingly and schedules the
`run_pass2` coroutine as a background task.  The status endpoint
returns real‑time progress information from the shared
`PASS2_PROGRESS` dictionary or, if no entry exists, computes a
summary from the database.
"""

from __future__ import annotations

from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session_factory
from ..models import Session as SessionModel, Chunk as ChunkModel, Clarification as ClarificationModel, Finding as FindingModel
from ..services.pass2_processor import run_pass2, PASS2_PROGRESS


router = APIRouter(prefix="/api", tags=["pass2"])


async def get_db() -> AsyncSession:
    if async_session_factory is None:
        raise HTTPException(status_code=500, detail="Database is not configured")
    async with async_session_factory() as session:
        yield session


@router.post("/sessions/{session_id}/review")
async def start_pass2(
    session_id: str,
    selected_chunks: List[str],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Start the Pass 2 deep review job for a session.

    This endpoint marks the specified chunks as selected for deep
    review by setting `pass2_selected` to True on those chunks and
    clearing the flag on all others.  It then schedules the
    `run_pass2` coroutine in a background task and returns a simple
    status response.  If the session is already in progress or
    completed, an error is returned.
    """
    # Validate session
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session_obj: SessionModel | None = result.scalar_one_or_none()
    if session_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session_obj.status not in ('section_selection', 'mapping', 'roles_assigned', 'uploading'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pass 2 cannot be started at this stage")
    # Update chunk selections
    res_chunks = await db.execute(select(ChunkModel).where(ChunkModel.session_id == session_id))
    chunks = res_chunks.scalars().all()
    selected_set = set(selected_chunks)
    for chunk in chunks:
        chunk.pass2_selected = (str(chunk.id) in selected_set)
        chunk.pass2_status = None  # reset any previous status
    await db.commit()
    # Kick off background job
    background_tasks.add_task(run_pass2, session_id)
    # Record initial progress entry
    PASS2_PROGRESS[str(session_id)] = {
        "status": "queued",
        "total_selected": len(selected_chunks),
        "completed_selected": 0,
        "current_document": None,
        "current_pages": None,
        "pending_clarifications": 0,
        "log": [],
        "critical_count": 0,
        "moderate_count": 0,
        "minor_count": 0,
    }
    return {"status": "started", "selected_chunks": len(selected_chunks)}


@router.get("/sessions/{session_id}/pass2/status")
async def pass2_status(session_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Return Pass 2 progress information for a session.

    If the session is currently running or queued, the returned
    structure mirrors that produced by the background job in
    `PASS2_PROGRESS`.  If the job has not started or has finished
    and progress entry has been removed, a summary is computed
    directly from the database.
    """
    key = str(session_id)
    if key in PASS2_PROGRESS:
        return PASS2_PROGRESS[key]
    # Compute a summary from the DB
    res_tot = await db.execute(
        select(func.count()).select_from(ChunkModel).where(
            ChunkModel.session_id == session_id,
            ChunkModel.pass2_selected.is_(True),
        )
    )
    total_selected = res_tot.scalar() or 0
    res_completed = await db.execute(
        select(func.count()).select_from(ChunkModel).where(
            ChunkModel.session_id == session_id,
            ChunkModel.pass2_selected.is_(True),
            ChunkModel.pass2_status == 'complete',
        )
    )
    completed = res_completed.scalar() or 0
    res_pending = await db.execute(
        select(func.count()).select_from(ClarificationModel).where(
            ClarificationModel.session_id == session_id,
            ClarificationModel.status == 'pending',
        )
    )
    pending = res_pending.scalar() or 0
    res_crit = await db.execute(
        select(func.count()).select_from(FindingModel).where(
            FindingModel.session_id == session_id,
            FindingModel.severity == 'Critical',
        )
    )
    crit_count = res_crit.scalar() or 0
    res_mod = await db.execute(
        select(func.count()).select_from(FindingModel).where(
            FindingModel.session_id == session_id,
            FindingModel.severity == 'Moderate',
        )
    )
    mod_count = res_mod.scalar() or 0
    res_min = await db.execute(
        select(func.count()).select_from(FindingModel).where(
            FindingModel.session_id == session_id,
            FindingModel.severity == 'Minor',
        )
    )
    min_count = res_min.scalar() or 0
    res_sess = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    sess = res_sess.scalar_one_or_none()
    status_str = sess.status if sess else 'unknown'
    return {
        "status": status_str,
        "total_selected": total_selected,
        "completed_selected": completed,
        "current_document": None,
        "current_pages": None,
        "pending_clarifications": pending,
        "log": [],
        "critical_count": crit_count,
        "moderate_count": mod_count,
        "minor_count": min_count,
    }
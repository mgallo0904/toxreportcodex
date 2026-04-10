"""API router for clarifications.

This module exposes endpoints for retrieving, answering and
dismissing clarification questions generated during Pass 2.  The
clarification lifecycle is simple: a question begins in the
`pending` state and transitions to either `answered` when the
user provides an answer, or `dismissed` when the question is
considered irrelevant.  Answered or dismissed clarifications are
not presented again, and their resolution triggers continuation
of the review pipeline.
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session_factory
from ..models import (
    Clarification as ClarificationModel,
    Chunk as ChunkModel,
    Document as DocumentModel,
)
from ..schemas.clarification import ClarificationResponse, ClarificationAnswer
from ..services.pass2_processor import PASS2_PROGRESS


router = APIRouter(prefix="/api", tags=["clarifications"])


async def get_db() -> AsyncSession:
    """Dependency that provides a database session for each request."""
    if async_session_factory is None:
        raise HTTPException(status_code=500, detail="Database is not configured")
    async with async_session_factory() as session:
        yield session


@router.get("/sessions/{session_id}/clarifications", response_model=List[ClarificationResponse])
async def list_clarifications(
    session_id: str,
    status_filter: Optional[str] = Query(None, description="Optionally filter clarifications by status"),
    db: AsyncSession = Depends(get_db),
) -> List[ClarificationResponse]:
    """Return all clarifications for a session.

    If a status filter is provided (e.g. `pending`, `answered`, `dismissed`),
    only clarifications with that status are returned.  Each
    clarification includes the originating document name and page
    range for ease of display in the UI.
    """
    # Build base query
    stmt = select(ClarificationModel).where(ClarificationModel.session_id == session_id)
    if status_filter:
        stmt = stmt.where(ClarificationModel.status == status_filter)
    result = await db.execute(stmt)
    clarifs = result.scalars().all()
    # Preload chunks
    chunk_ids = {c.chunk_id for c in clarifs if c.chunk_id is not None}
    chunk_map = {}
    if chunk_ids:
        res_chunks = await db.execute(
            select(ChunkModel).where(ChunkModel.id.in_(chunk_ids))
        )
        for ch in res_chunks.scalars():
            chunk_map[ch.id] = ch
    # Build document mapping
    doc_ids_set = {chunk.document_id for chunk in chunk_map.values() if chunk.document_id is not None}
    doc_map = {}
    if doc_ids_set:
        res_docs = await db.execute(
            select(DocumentModel.id, DocumentModel.original_filename).where(DocumentModel.id.in_(doc_ids_set))
        )
        for doc_id, filename in res_docs:
            doc_map[doc_id] = filename
    responses: List[ClarificationResponse] = []
    for clar in clarifs:
        doc_name: Optional[str] = None
        page_range: Optional[str] = None
        if clar.chunk_id:
            chunk = chunk_map.get(clar.chunk_id)
            if chunk:
                doc_name = doc_map.get(chunk.document_id)
                if chunk.page_start is not None and chunk.page_end is not None:
                    page_range = f"{chunk.page_start}-{chunk.page_end}"
                elif chunk.page_start is not None:
                    page_range = str(chunk.page_start)
        responses.append(
            ClarificationResponse(
                id=str(clar.id),
                session_id=str(clar.session_id),
                chunk_id=str(clar.chunk_id) if clar.chunk_id else None,
                question_text=clar.question_text,
                status=clar.status,
                answer_text=clar.answer_text,
                answered_at=clar.answered_at,
                created_at=clar.created_at,
                document_name=doc_name,
                page_range=page_range,
            )
        )
    return responses


@router.post("/clarifications/{clarification_id}/answer", response_model=ClarificationResponse)
async def answer_clarification(
    clarification_id: str,
    payload: ClarificationAnswer,
    db: AsyncSession = Depends(get_db),
) -> ClarificationResponse:
    """Record an answer to a clarification.

    The clarification status is set to `answered`, the answer text is
    stored, and the answered timestamp is recorded.  Once answered,
    the clarification will no longer block the Pass 2 processing for
    its associated chunk.
    """
    result = await db.execute(
        select(ClarificationModel).where(ClarificationModel.id == clarification_id)
    )
    clar: ClarificationModel | None = result.scalar_one_or_none()
    if clar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification not found")
    if clar.status != 'pending':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clarification already resolved")
    clar.status = 'answered'
    clar.answer_text = payload.answer_text
    clar.answered_at = datetime.datetime.utcnow()
    await db.commit()
    # Update progress pending count if tracking exists
    sess_id_str = str(clar.session_id)
    if sess_id_str in PASS2_PROGRESS:
        # Recompute number of pending clarifications for the session
        pending = await db.execute(
            select(ClarificationModel).where(
                ClarificationModel.session_id == clar.session_id,
                ClarificationModel.status == 'pending',
            )
        )
        pending_count = len(pending.scalars().all())
        PASS2_PROGRESS[sess_id_str]["pending_clarifications"] = pending_count
    # Prepare response with doc and page information
    doc_name = None
    page_range = None
    if clar.chunk_id:
        res_chunk = await db.execute(
            select(ChunkModel).where(ChunkModel.id == clar.chunk_id)
        )
        chunk = res_chunk.scalar_one_or_none()
        if chunk:
            res_doc = await db.execute(
                select(DocumentModel).where(DocumentModel.id == chunk.document_id)
            )
            doc = res_doc.scalar_one_or_none()
            if doc:
                doc_name = doc.original_filename
            if chunk.page_start is not None and chunk.page_end is not None:
                page_range = f"{chunk.page_start}-{chunk.page_end}"
            elif chunk.page_start is not None:
                page_range = str(chunk.page_start)
    return ClarificationResponse(
        id=str(clar.id),
        session_id=str(clar.session_id),
        chunk_id=str(clar.chunk_id) if clar.chunk_id else None,
        question_text=clar.question_text,
        status=clar.status,
        answer_text=clar.answer_text,
        answered_at=clar.answered_at,
        created_at=clar.created_at,
        document_name=doc_name,
        page_range=page_range,
    )


@router.post("/clarifications/{clarification_id}/dismiss", response_model=ClarificationResponse)
async def dismiss_clarification(
    clarification_id: str,
    db: AsyncSession = Depends(get_db),
) -> ClarificationResponse:
    """Dismiss a clarification as irrelevant.

    Dismissed clarifications are considered irrelevant.  All findings
    produced from the corresponding chunk will be marked as having
    low confidence once processing resumes.
    """
    result = await db.execute(
        select(ClarificationModel).where(ClarificationModel.id == clarification_id)
    )
    clar: ClarificationModel | None = result.scalar_one_or_none()
    if clar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification not found")
    if clar.status != 'pending':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clarification already resolved")
    clar.status = 'dismissed'
    clar.answer_text = None
    clar.answered_at = datetime.datetime.utcnow()
    await db.commit()
    # Update progress pending count
    sess_id_str = str(clar.session_id)
    if sess_id_str in PASS2_PROGRESS:
        pending = await db.execute(
            select(ClarificationModel).where(
                ClarificationModel.session_id == clar.session_id,
                ClarificationModel.status == 'pending',
            )
        )
        pending_count = len(pending.scalars().all())
        PASS2_PROGRESS[sess_id_str]["pending_clarifications"] = pending_count
    doc_name = None
    page_range = None
    if clar.chunk_id:
        res_chunk = await db.execute(
            select(ChunkModel).where(ChunkModel.id == clar.chunk_id)
        )
        chunk = res_chunk.scalar_one_or_none()
        if chunk:
            res_doc = await db.execute(
                select(DocumentModel).where(DocumentModel.id == chunk.document_id)
            )
            doc = res_doc.scalar_one_or_none()
            if doc:
                doc_name = doc.original_filename
            if chunk.page_start is not None and chunk.page_end is not None:
                page_range = f"{chunk.page_start}-{chunk.page_end}"
            elif chunk.page_start is not None:
                page_range = str(chunk.page_start)
    return ClarificationResponse(
        id=str(clar.id),
        session_id=str(clar.session_id),
        chunk_id=str(clar.chunk_id) if clar.chunk_id else None,
        question_text=clar.question_text,
        status=clar.status,
        answer_text=clar.answer_text,
        answered_at=clar.answered_at,
        created_at=clar.created_at,
        document_name=doc_name,
        page_range=page_range,
    )
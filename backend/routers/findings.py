"""API router for findings.

Findings represent issues identified during Pass 2.  This router
provides endpoints to list all findings for a session, retrieve
details of a single finding, and confirm or reject individual
findings.  Users may optionally override the category, comment,
recommendation or severity when confirming a finding.  Rejected
findings are retained for audit purposes but will not be used in
fine‑tuning.
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import io
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session_factory
from ..models import (
    Finding as FindingModel,
    Chunk as ChunkModel,
    Document as DocumentModel,
)
from ..services.export_service import export_findings_to_excel
from ..schemas.finding import FindingResponse, FindingUpdate


router = APIRouter(prefix="/api", tags=["findings"])


async def get_db() -> AsyncSession:
    """Dependency to provide an async DB session."""
    if async_session_factory is None:
        raise HTTPException(status_code=500, detail="Database is not configured")
    async with async_session_factory() as session:
        yield session


@router.get("/sessions/{session_id}/findings", response_model=List[FindingResponse])
async def list_findings(
    session_id: str,
    severity: Optional[str] = Query(None, description="Filter by severity: Critical, Moderate or Minor"),
    category: Optional[str] = Query(None, description="Filter by finding category"),
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    confidence: Optional[str] = Query(None, description="Filter by confidence: standard or low"),
    confirmed: Optional[str] = Query(
        None,
        description="Filter by confirmation state: true, false or null for undecided",
    ),
    db: AsyncSession = Depends(get_db),
) -> List[FindingResponse]:
    """Retrieve all findings for a session with optional filters.

    Query parameters allow filtering by severity, confidence level and
    confirmation status.  The confirmation filter accepts 'true',
    'false' or 'null' (case insensitive) to match values of
    `confirmed_correct`.
    """
    stmt = select(FindingModel).where(FindingModel.session_id == session_id)
    # Apply filters when provided
    if severity:
        stmt = stmt.where(FindingModel.severity == severity)
    if category:
        stmt = stmt.where(FindingModel.category == category)
    if document_id:
        stmt = stmt.where(FindingModel.document_id == document_id)
    if confidence:
        stmt = stmt.where(FindingModel.confidence == confidence)
    if confirmed is not None:
        ci = confirmed.strip().lower() if isinstance(confirmed, str) else str(confirmed).lower()
        if ci == 'true':
            stmt = stmt.where(FindingModel.confirmed_correct.is_(True))
        elif ci == 'false':
            stmt = stmt.where(FindingModel.confirmed_correct.is_(False))
        elif ci in ('none', 'null', ''):
            stmt = stmt.where(FindingModel.confirmed_correct.is_(None))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid confirmed filter")
    result = await db.execute(stmt)
    findings = result.scalars().all()
    # Preload chunk and document info to build page_range and doc_name
    chunk_ids = {f.chunk_id for f in findings if f.chunk_id is not None}
    chunk_map = {}
    if chunk_ids:
        res_chunks = await db.execute(
            select(ChunkModel).where(ChunkModel.id.in_(chunk_ids))
        )
        for chunk in res_chunks.scalars():
            chunk_map[chunk.id] = chunk
    doc_ids = {chunk.document_id for chunk in chunk_map.values() if chunk.document_id is not None}
    doc_map = {}
    if doc_ids:
        res_docs = await db.execute(
            select(DocumentModel.id, DocumentModel.original_filename).where(DocumentModel.id.in_(doc_ids))
        )
        for doc_id, filename in res_docs:
            doc_map[doc_id] = filename
    responses: List[FindingResponse] = []
    for f in findings:
        doc_name = None
        page_range = None
        if f.chunk_id:
            ch = chunk_map.get(f.chunk_id)
            if ch:
                doc_name = doc_map.get(ch.document_id)
                if ch.page_start is not None and ch.page_end is not None:
                    page_range = f"{ch.page_start}-{ch.page_end}"
                elif ch.page_start is not None:
                    page_range = str(ch.page_start)
        responses.append(
            FindingResponse(
                id=str(f.id),
                session_id=str(f.session_id),
                chunk_id=str(f.chunk_id) if f.chunk_id else None,
                document_id=str(f.document_id) if f.document_id else None,
                finding_label=f.finding_label,
                page_section_table=f.page_section_table,
                original_text=f.original_text,
                category=f.category,
                comment=f.comment,
                recommendation=f.recommendation,
                severity=f.severity,
                source_reference=f.source_reference,
                confidence=f.confidence,
                confirmed_correct=f.confirmed_correct,
                confirmed_at=f.confirmed_at,
                is_seed=f.is_seed,
                created_at=f.created_at,
                document_name=doc_name,
                page_range=page_range,
            )
        )
    return responses


@router.get("/findings/{finding_id}", response_model=FindingResponse)
async def get_finding(finding_id: str, db: AsyncSession = Depends(get_db)) -> FindingResponse:
    """Retrieve a single finding by ID."""
    result = await db.execute(
        select(FindingModel).where(FindingModel.id == finding_id)
    )
    finding: FindingModel | None = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    # Build doc_name and page_range
    doc_name = None
    page_range = None
    if finding.chunk_id:
        res_chunk = await db.execute(
            select(ChunkModel).where(ChunkModel.id == finding.chunk_id)
        )
        ch = res_chunk.scalar_one_or_none()
        if ch:
            res_doc = await db.execute(
                select(DocumentModel).where(DocumentModel.id == ch.document_id)
            )
            doc = res_doc.scalar_one_or_none()
            if doc:
                doc_name = doc.original_filename
            if ch.page_start is not None and ch.page_end is not None:
                page_range = f"{ch.page_start}-{ch.page_end}"
            elif ch.page_start is not None:
                page_range = str(ch.page_start)
    return FindingResponse(
        id=str(finding.id),
        session_id=str(finding.session_id),
        chunk_id=str(finding.chunk_id) if finding.chunk_id else None,
        document_id=str(finding.document_id) if finding.document_id else None,
        finding_label=finding.finding_label,
        page_section_table=finding.page_section_table,
        original_text=finding.original_text,
        category=finding.category,
        comment=finding.comment,
        recommendation=finding.recommendation,
        severity=finding.severity,
        source_reference=finding.source_reference,
        confidence=finding.confidence,
        confirmed_correct=finding.confirmed_correct,
        confirmed_at=finding.confirmed_at,
        is_seed=finding.is_seed,
        created_at=finding.created_at,
        document_name=doc_name,
        page_range=page_range,
    )


@router.post("/findings/{finding_id}/confirm", response_model=FindingResponse)
async def confirm_finding(
    finding_id: str,
    update: FindingUpdate,
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    """Confirm or reject a finding with optional modifications.

    The request body must include the `confirm` flag indicating whether
    the finding is correct (True) or incorrect (False).  Optionally,
    the user may override certain fields prior to confirmation.  Once
    confirmed or rejected, the `confirmed_correct` and `confirmed_at`
    fields are updated accordingly.
    """
    result = await db.execute(
        select(FindingModel).where(FindingModel.id == finding_id)
    )
    finding: FindingModel | None = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    # Update fields if provided
    if update.category is not None:
        finding.category = update.category
    if update.comment is not None:
        finding.comment = update.comment
    if update.recommendation is not None:
        finding.recommendation = update.recommendation
    if update.severity is not None:
        finding.severity = update.severity
    # Set confirmation
    finding.confirmed_correct = update.confirm
    finding.confirmed_at = datetime.datetime.utcnow()
    await db.commit()
    # Build response
    doc_name = None
    page_range = None
    if finding.chunk_id:
        res_chunk = await db.execute(
            select(ChunkModel).where(ChunkModel.id == finding.chunk_id)
        )
        ch = res_chunk.scalar_one_or_none()
        if ch:
            res_doc = await db.execute(
                select(DocumentModel).where(DocumentModel.id == ch.document_id)
            )
            doc = res_doc.scalar_one_or_none()
            if doc:
                doc_name = doc.original_filename
            if ch.page_start is not None and ch.page_end is not None:
                page_range = f"{ch.page_start}-{ch.page_end}"
            elif ch.page_start is not None:
                page_range = str(ch.page_start)
    return FindingResponse(
        id=str(finding.id),
        session_id=str(finding.session_id),
        chunk_id=str(finding.chunk_id) if finding.chunk_id else None,
        document_id=str(finding.document_id) if finding.document_id else None,
        finding_label=finding.finding_label,
        page_section_table=finding.page_section_table,
        original_text=finding.original_text,
        category=finding.category,
        comment=finding.comment,
        recommendation=finding.recommendation,
        severity=finding.severity,
        source_reference=finding.source_reference,
        confidence=finding.confidence,
        confirmed_correct=finding.confirmed_correct,
        confirmed_at=finding.confirmed_at,
        is_seed=finding.is_seed,
        created_at=finding.created_at,
        document_name=doc_name,
        page_range=page_range,
    )


# -----------------------------------------------------------------------------
# Export endpoint
# -----------------------------------------------------------------------------

@router.get("/sessions/{session_id}/findings/export")
async def export_findings(
    session_id: str,
    severity: Optional[str] = Query(None, description="Filter by severity: Critical, Moderate or Minor"),
    category: Optional[str] = Query(None, description="Filter by finding category"),
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    confidence: Optional[str] = Query(None, description="Filter by confidence: standard or low"),
    confirmed: Optional[str] = Query(None, description="Filter by confirmation state: true, false or null"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Download an Excel file of findings and clarifications for a session.

    The first worksheet includes findings filtered by the supplied
    query parameters.  The second worksheet contains the full
    clarification log for the session regardless of filters.  See
    :mod:`backend.services.export_service` for implementation details.
    """
    # Assemble filters dictionary; None values will be ignored by the service
    filters = {
        "severity": severity,
        "category": category,
        "document_id": document_id,
        "confidence": confidence,
        "confirmed": confirmed,
    }
    excel_bytes = await export_findings_to_excel(session_id, filters, db)
    filename = f"session_{session_id}_findings.xlsx"
    # Return a streaming response with correct content type and disposition
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
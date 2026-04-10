"""FastAPI routes for Pass 1 processing and data retrieval.

This router exposes endpoints to start the structural mapping phase,
monitor progress, and retrieve intermediate data such as the document
outline, claims and conflicts.  These endpoints are prefixed with
`/api/sessions/{session_id}` and operate on a specific session.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import (
    Session as SessionModel,
    Document as DocumentModel,
    Chunk as ChunkModel,
    DocumentSection as DocumentSectionModel,
    Claim as ClaimModel,
    Conflict as ConflictModel,
)
from ..schemas.section import DocumentOutline, SectionNode
from ..schemas.claim import ClaimResponse
from ..schemas.conflict import ConflictResponse
from ..services.pass1_processor import run_pass1, PASS1_PROGRESS

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["pass1"])


@router.post("/confirm")
async def confirm_session(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Validate role assignment and launch the structural mapping job.

    This endpoint ensures that every document in the session has an assigned
    role.  If validation passes, the session status is set to
    `mapping`, `pass1_started_at` is recorded, and a background task
    is scheduled to run Pass 1.  The caller receives a job identifier
    (which is the session ID) and the new status.
    """
    # Fetch session
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session_obj = result.scalar_one_or_none()
    if session_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    # Ensure all documents have an assigned role
    result_docs = await db.execute(select(DocumentModel).where(DocumentModel.session_id == session_id))
    docs = result_docs.scalars().all()
    for doc in docs:
        if not doc.assigned_role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All documents must have an assigned role before mapping")
    # Update status and start timestamp
    session_obj.status = "mapping"
    session_obj.pass1_started_at = None  # will be set in job
    await db.commit()
    # Launch background job
    background_tasks.add_task(run_pass1, str(session_id))
    return {"status": "mapping", "job_id": str(session_id)}


@router.get("/pass1/status")
async def get_pass1_status(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return the current progress of the Pass 1 job.

    Reads from the in‑memory `PASS1_PROGRESS` dictionary populated by
    `run_pass1`.  If no entry exists yet, attempts to derive progress
    from the database state.  The returned JSON includes overall
    status, total and completed chunk counts, the document and page
    range currently being processed, a log of completed chunks, and
    the number of conflicts detected so far.
    """
    key = str(session_id)
    progress = PASS1_PROGRESS.get(key)
    if progress:
        return progress
    # Fallback: derive status from DB
    result_session = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session_obj = result_session.scalar_one_or_none()
    if session_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    # Compute counts
    result_total = await db.execute(select(ChunkModel).where(ChunkModel.session_id == session_id))
    chunks = result_total.scalars().all()
    total = len(chunks)
    completed = sum(1 for c in chunks if c.pass1_status == "complete")
    # Conflicts
    result_conf = await db.execute(select(ConflictModel).where(ConflictModel.session_id == session_id))
    conflicts = result_conf.scalars().all()
    # Compute sections and claims counts for summary when mapping is complete
    sections_count = 0
    claims_count = 0
    try:
        result_secs = await db.execute(select(DocumentSectionModel).where(DocumentSectionModel.session_id == session_id))
        sections_count = len(result_secs.scalars().all())
        result_clms = await db.execute(select(ClaimModel).where(ClaimModel.session_id == session_id))
        claims_count = len(result_clms.scalars().all())
    except Exception:
        pass
    return {
        "status": session_obj.status,
        "total_chunks": total,
        "completed_chunks": completed,
        "current_document": None,
        "current_pages": None,
        "log": [],
        "conflicts_found": len(conflicts),
        "sections_indexed": sections_count,
        "claims_extracted": claims_count,
    }


@router.get("/outline", response_model=Dict[str, List[DocumentOutline]])
async def get_outline(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return the hierarchical outline of all documents in the session.

    The response has a single key `documents` whose value is a list of
    document outlines.  Each outline includes the document ID,
    filename, assigned role and a nested list of sections (with
    children).  Sections are ordered by their appearance within the
    document.
    """
    # Query documents for session
    result_docs = await db.execute(select(DocumentModel).where(DocumentModel.session_id == session_id))
    documents = result_docs.scalars().all()
    outlines: List[DocumentOutline] = []
    for doc in documents:
        # Fetch sections for document ordered by level then insertion
        result_secs = await db.execute(select(DocumentSectionModel).where(DocumentSectionModel.document_id == doc.id))
        secs = result_secs.scalars().all()
        # Build SectionNode objects and parent/child relationships
        node_map = {sec.id: SectionNode.from_orm(sec) for sec in secs}
        # Initialise children lists
        for node in node_map.values():
            node.children = []
        children_map: Dict[uuid.UUID, List[SectionNode]] = {sid: [] for sid in node_map.keys()}
        for sec in secs:
            if sec.parent_section_id and sec.parent_section_id in node_map:
                children_map[sec.parent_section_id].append(node_map[sec.id])
        # Assign children to each node
        for sid, child_list in children_map.items():
            node_map[sid].children = child_list
        # Determine top-level sections (no parent_section_id)
        roots: List[SectionNode] = [node_map[sec.id] for sec in secs if not sec.parent_section_id]
        outline = DocumentOutline(
            id=doc.id,
            filename=doc.original_filename,
            role=doc.assigned_role,
            sections=roots,
        )
        outlines.append(outline)
    return {"documents": outlines}


@router.get("/claims", response_model=List[ClaimResponse])
async def list_claims(
    session_id: uuid.UUID,
    document_id: Optional[uuid.UUID] = Query(None, description="Filter by document ID"),
    parameter_type: Optional[str] = Query(None, description="Filter by parameter type"),
    db: AsyncSession = Depends(get_db),
):
    """Return all claims for a session with optional filtering.

    Clients can filter by `document_id` and/or `parameter_type`.  The
    response is a flat list of claims.
    """
    query = select(ClaimModel).where(ClaimModel.session_id == session_id)
    if document_id:
        query = query.where(ClaimModel.document_id == document_id)
    if parameter_type:
        query = query.where(ClaimModel.parameter_type == parameter_type)
    result = await db.execute(query)
    claims = result.scalars().all()
    return [ClaimResponse.from_orm(c) for c in claims]


@router.get("/conflicts", response_model=List[ConflictResponse])
async def list_conflicts(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return all conflicts detected in the session.

    Each conflict includes the names of the documents where the
    conflicting values were found, in addition to the raw IDs.
    """
    result = await db.execute(select(ConflictModel).where(ConflictModel.session_id == session_id))
    conflicts = result.scalars().all()
    # Build a lookup of document names
    result_docs = await db.execute(select(DocumentModel).where(DocumentModel.session_id == session_id))
    doc_map = {d.id: d.original_filename for d in result_docs.scalars().all()}
    conflict_responses: List[ConflictResponse] = []
    for conf in conflicts:
        response = ConflictResponse(
            id=conf.id,
            session_id=conf.session_id,
            parameter_name=conf.parameter_name,
            value_a=conf.value_a,
            document_id_a=conf.document_id_a,
            document_name_a=doc_map.get(conf.document_id_a),
            chunk_id_a=conf.chunk_id_a,
            page_a=conf.page_a,
            value_b=conf.value_b,
            document_id_b=conf.document_id_b,
            document_name_b=doc_map.get(conf.document_id_b),
            chunk_id_b=conf.chunk_id_b,
            page_b=conf.page_b,
            resolved=conf.resolved,
        )
        conflict_responses.append(response)
    return conflict_responses

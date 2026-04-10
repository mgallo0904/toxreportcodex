"""API routes for session resources.

These endpoints allow clients to create new review sessions and list
existing sessions. Session creation records the basic study metadata
needed to begin a review. Listing sessions returns the summary
information required for the UI. Detailed session retrieval includes
attached documents. Deletion is not implemented in Phase 2 and will be
added in a later phase.
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Session as SessionModel, Document as DocumentModel
from ..schemas.session import SessionCreate, SessionSummary, SessionDetail
from ..schemas.document import DocumentResponse


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionSummary, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionSummary:
    """Create a new review session.

    A new Session is inserted with the provided study metadata and
    returned to the client. The initial status is 'uploading'.
    """
    session = SessionModel(
        study_name=payload.study_name,
        study_type=payload.study_type,
        draft_maturity=payload.draft_maturity,
        priority_notes=payload.priority_notes,
        status="uploading",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session  # response_model handles serialization


@router.get("", response_model=List[SessionSummary])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> List[SessionSummary]:
    """Return all sessions ordered by creation time descending."""
    result = await db.execute(select(SessionModel).order_by(SessionModel.created_at.desc()))
    sessions = result.scalars().all()
    return sessions


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SessionDetail:
    """Retrieve a single session by its ID, including associated documents."""
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session_obj = result.scalar_one_or_none()
    if session_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    # Eagerly load documents
    result_docs = await db.execute(select(DocumentModel).where(DocumentModel.session_id == session_id))
    documents = result_docs.scalars().all()
    # Convert documents to Pydantic models
    doc_responses = [DocumentResponse.from_orm(doc) for doc in documents]
    detail = SessionDetail.from_orm(session_obj)
    detail.documents = doc_responses
    return detail


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a session and all associated data.

    This endpoint removes the session from the database along with all
    related documents, chunks, claims, findings and clarifications.
    It also attempts to remove any files on disk belonging to the
    session stored under the configured ``storage_path``.
    """
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session_obj: SessionModel | None = result.scalar_one_or_none()
    if session_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    # Delete the session (cascade deletes children)
    await db.delete(session_obj)
    await db.commit()
    # Remove file storage directory if configured and exists
    try:
        from ..config import get_settings
        import os
        import shutil
        settings = get_settings()
        storage_path = getattr(settings, "storage_path", None)
        if storage_path:
            # Compose session directory path (session_id as string)
            dir_path = os.path.join(storage_path, str(session_id))
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path, ignore_errors=True)
    except Exception:
        # Swallow any errors during filesystem cleanup
        pass
    return None
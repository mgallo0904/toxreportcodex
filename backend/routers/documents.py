"""API routes for document resources.

These endpoints support uploading files to a session, retrieving the
documents in a session and updating or deleting individual documents.
Uploaded files are saved to disk in the configured storage path and
then chunked using the services defined in `backend.services.chunker`.
"""

from __future__ import annotations

import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..models import Session as SessionModel, Document as DocumentModel, Chunk
from ..schemas.document import DocumentResponse, DocumentUpdate
from ..services.chunker import process_document_file


router = APIRouter(prefix="/api/sessions/{session_id}/documents", tags=["documents"])


def secure_filename(filename: str) -> str:
    """Sanitise a filename by stripping potentially dangerous characters."""
    return os.path.basename(filename.replace("..", ""))


@router.post("", response_model=List[DocumentResponse])
async def upload_documents(
    session_id: uuid.UUID,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """Upload one or more documents to a session.

    Each file is stored on disk within the session's storage directory,
    a Document record is created in the database and the file is
    immediately chunked. Returns the created documents with chunk counts.
    """
    # Validate session exists
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session_obj = result.scalar_one_or_none()
    if session_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    settings = get_settings()
    storage_root = os.path.join(settings.storage_path, str(session_id))
    os.makedirs(storage_root, exist_ok=True)
    created_docs: List[DocumentModel] = []
    for upload in files:
        filename = secure_filename(upload.filename)
        # Determine format from extension
        ext = filename.rsplit('.', 1)[-1].lower()
        if ext not in {"pdf", "docx", "xlsx"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file type: {ext}")
        # Create Document record first
        document = DocumentModel(
            session_id=session_id,
            original_filename=filename,
            format=ext,
        )
        db.add(document)
        await db.flush()  # get document.id
        # Build file path and save
        doc_dir = os.path.join(storage_root, str(document.id))
        os.makedirs(doc_dir, exist_ok=True)
        file_path = os.path.join(doc_dir, filename)
        content = await upload.read()
        with open(file_path, "wb") as f:
            f.write(content)
        document.file_path = file_path
        # Chunk file
        await process_document_file(document, file_path, db)
        created_docs.append(document)
    # Commit all changes
    await db.commit()
    # Refresh and return
    for doc in created_docs:
        await db.refresh(doc)
    return created_docs


@router.get("", response_model=List[DocumentResponse])
async def list_documents(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> List[DocumentResponse]:
    """Return all documents for a given session."""
    result = await db.execute(select(DocumentModel).where(DocumentModel.session_id == session_id))
    docs = result.scalars().all()
    return docs


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    session_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Update a document's assigned role and optional role label."""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == document_id, DocumentModel.session_id == session_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if payload.assigned_role is not None:
        document.assigned_role = payload.assigned_role
    if payload.role_label is not None:
        document.role_label = payload.role_label
    # Persist document changes
    await db.commit()
    await db.refresh(document)
    # If all documents in this session now have assigned roles, update the session status
    # to indicate role assignment is complete.  This helps drive the UI state machine.
    missing_roles_result = await db.execute(
        select(DocumentModel).where(
            DocumentModel.session_id == session_id,
            DocumentModel.assigned_role.is_(None),
        )
    )
    missing_docs = missing_roles_result.scalars().all()
    if not missing_docs:
        # Update session status
        session_obj = await db.get(SessionModel, session_id)
        if session_obj and session_obj.status == "uploading":
            session_obj.status = "roles_assigned"
            await db.commit()
    return document


@router.delete("/{document_id}")
async def delete_document(
    session_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Delete a document and its associated chunks and file from disk."""
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == document_id, DocumentModel.session_id == session_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Delete file from disk if present
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
            # Remove parent directory if empty
            parent_dir = os.path.dirname(document.file_path)
            if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                os.rmdir(parent_dir)
        except OSError:
            pass
    # Delete chunks will cascade on delete due to foreign key
    await db.delete(document)
    await db.commit()
    return JSONResponse(content={"deleted": True})
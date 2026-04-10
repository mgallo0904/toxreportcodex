"""API router for dataset export.

Provides endpoints to export fine‑tuning datasets derived from
confirmed findings.  Datasets are returned as JSON arrays of
objects; clients may further transform them into JSONL or other
formats as required for training.
"""

from __future__ import annotations

from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import async_session_factory
from ..models import Session as SessionModel, Finding as FindingModel
from ..services.dataset_builder import export_session_dataset


router = APIRouter(prefix="/api", tags=["dataset"])


async def get_db() -> AsyncSession:
    if async_session_factory is None:
        raise HTTPException(status_code=500, detail="Database is not configured")
    async with async_session_factory() as session:
        yield session


@router.get("/sessions/{session_id}/dataset", response_model=List[Dict[str, Any]])
async def get_dataset(session_id: str, db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return a dataset for a session consisting of confirmed findings.

    Only findings with `confirmed_correct` set to True are included.
    If no such findings exist, an empty list is returned.
    """
    # Validate session
    result = await db.execute(select(SessionModel.id).where(SessionModel.id == session_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    dataset = await export_session_dataset(db, session_id)
    return dataset
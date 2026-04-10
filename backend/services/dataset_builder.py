"""Dataset builder service.

This module provides helper functions to assemble fine‑tuning datasets
from confirmed findings.  Each confirmed finding produces a single
training example that pairs the source text (chunk) with the
annotated labels.  The resulting dataset can be exported via the
dataset API and consumed by finetuning jobs.

Note: In this simplified implementation, the dataset is returned as
a list of dictionaries.  In a production system you might format
records for specific ML frameworks (e.g. JSONL) or include more
contextual information.
"""

from __future__ import annotations

from typing import List, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Finding as FindingModel,
    Chunk as ChunkModel,
    Document as DocumentModel,
)


async def export_session_dataset(db: AsyncSession, session_id: str) -> List[Dict[str, object]]:
    """Assemble a dataset for a single session.

    Only findings that have been confirmed as correct are included.
    Each record contains the chunk text, associated metadata and
    labels.  The keys used here are generic; consumers may adapt
    them as needed.

    Parameters
    ----------
    db: AsyncSession
        Active database session.
    session_id: str
        Session identifier.

    Returns
    -------
    List[Dict[str, object]]
        The dataset records.
    """
    # Query confirmed findings
    result = await db.execute(
        select(FindingModel).where(
            FindingModel.session_id == session_id,
            FindingModel.confirmed_correct.is_(True),
        )
    )
    findings = result.scalars().all()
    if not findings:
        return []
    # Preload chunks and documents
    chunk_ids = {f.chunk_id for f in findings if f.chunk_id is not None}
    chunk_map = {}
    if chunk_ids:
        res_chunks = await db.execute(
            select(ChunkModel).where(ChunkModel.id.in_(chunk_ids))
        )
        for ch in res_chunks.scalars():
            chunk_map[ch.id] = ch
    doc_ids = {chunk.document_id for chunk in chunk_map.values() if chunk.document_id is not None}
    doc_map = {}
    if doc_ids:
        res_docs = await db.execute(
            select(DocumentModel.id, DocumentModel.original_filename).where(DocumentModel.id.in_(doc_ids))
        )
        for doc_id, name in res_docs:
            doc_map[doc_id] = name
    dataset: List[Dict[str, object]] = []
    for f in findings:
        ch = chunk_map.get(f.chunk_id)
        doc_name = None
        page_range = None
        text = None
        if ch:
            text = ch.text_content
            doc_name = doc_map.get(ch.document_id)
            if ch.page_start is not None and ch.page_end is not None:
                page_range = f"{ch.page_start}-{ch.page_end}"
            elif ch.page_start is not None:
                page_range = str(ch.page_start)
        record: Dict[str, object] = {
            "session_id": str(f.session_id),
            "document_name": doc_name,
            "page_range": page_range,
            "finding_id": str(f.id),
            "finding_label": f.finding_label,
            "category": f.category,
            "comment": f.comment,
            "recommendation": f.recommendation,
            "severity": f.severity,
            "source_reference": f.source_reference,
            "chunk_text": text,
            "original_text": f.original_text,
        }
        dataset.append(record)
    return dataset
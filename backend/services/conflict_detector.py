"""Conflict detector service.

This module compares numerical claims extracted during Pass 1 across
documents in the same session.  It identifies parameters that have
conflicting values in different documents and creates Conflict
records accordingly.  When a conflict is detected, the associated
chunks are flagged for automatic inclusion in Pass 2 (deep review).
"""

from __future__ import annotations

from typing import Iterable, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Claim, Conflict, Chunk


NUMERIC_PARAMETER_TYPES = {
    "dose",
    "concentration",
    "n_count",
    "timepoint",
    "body_weight",
    "organ_weight",
    "stat_value",
}


async def detect_conflicts(session_id: str, db: AsyncSession) -> int:
    """Detect conflicting numerical claims within a session.

    Parameters
    ----------
    session_id: str
        The ID of the session to analyse.
    db: AsyncSession
        An active database session.

    Returns
    -------
    int
        The number of conflict records created.
    """
    # Query all numerical claims for this session
    result = await db.execute(
        select(Claim).where(
            Claim.session_id == session_id,
            Claim.parameter_type.in_(NUMERIC_PARAMETER_TYPES),
        )
    )
    claims: List[Claim] = list(result.scalars().all())
    # Group claims by parameter_name (case insensitive).  Ignore claims without a name.
    grouped: Dict[str, List[Claim]] = {}
    for claim in claims:
        if not claim.parameter_name:
            continue
        key = claim.parameter_name.strip().lower()
        grouped.setdefault(key, []).append(claim)
    conflict_count = 0
    # Iterate groups to find conflicts
    for param_name, group in grouped.items():
        # Partition by normalised value (strip whitespace and lower).  Use empty string for None.
        value_map: Dict[str, List[Claim]] = {}
        for claim in group:
            val_raw = claim.value or ""
            val_norm = "".join(val_raw.split()).lower()
            value_map.setdefault(val_norm, []).append(claim)
        # No conflict if only one distinct value
        if len(value_map) < 2:
            continue
        # Identify two distinct values to form a conflict record
        values = list(value_map.keys())
        # We'll create a single conflict using the first two distinct values
        val_a, val_b = values[0], values[1]
        claim_a = value_map[val_a][0]
        claim_b = value_map[val_b][0]
        # Create conflict
        conflict = Conflict(
            session_id=session_id,
            parameter_name=param_name,
            value_a=claim_a.value,
            document_id_a=claim_a.document_id,
            chunk_id_a=claim_a.chunk_id,
            page_a=claim_a.page_number,
            value_b=claim_b.value,
            document_id_b=claim_b.document_id,
            chunk_id_b=claim_b.chunk_id,
            page_b=claim_b.page_number,
        )
        db.add(conflict)
        conflict_count += 1
        # Mark involved chunks as automatically selected for Pass 2
        chunk_ids = {claim_a.chunk_id, claim_b.chunk_id}
        result_chunks = await db.execute(select(Chunk).where(Chunk.id.in_(chunk_ids)))
        for chunk in result_chunks.scalars().all():
            chunk.pass2_auto_selected = True
    # Persist new conflicts and chunk flags
    await db.commit()
    return conflict_count

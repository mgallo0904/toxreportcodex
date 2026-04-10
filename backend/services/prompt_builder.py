"""Prompt builder for Pass 2.

This module assembles the dynamic system prompt for the deep review
phase.  It loads the base template from the `prompts/pass2_reviewer.txt`
file and replaces variable placeholders with context derived from
database records.  Claim registries and conflict descriptions are
constructed from the results of Pass 1 and conflict detection.  If
histopathology content is detected (not implemented in this
reference), the INHAND reference block can be populated accordingly.

The returned tuple contains the final system prompt and an empty
string for the user content.  The caller should pass both values to
`InferenceClient.complete`.
"""

from __future__ import annotations

import os
from typing import Tuple, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Session as SessionModel,
    Chunk as ChunkModel,
    Document as DocumentModel,
    Claim as ClaimModel,
    Conflict as ConflictModel,
)

# List of claim parameter types considered numeric for Pass 2.  Only
# these parameter types are included in the claim registry block.  It
# must mirror the definitions used in the structural mapping phase.
NUMERIC_PARAMETER_TYPES = [
    "dose",
    "concentration",
    "n_count",
    "timepoint",
    "body_weight",
    "organ_weight",
    "stat_value",
]


async def build_pass2_prompt(
    db: AsyncSession,
    session_obj: SessionModel,
    chunk_obj: ChunkModel,
) -> Tuple[str, str]:
    """Assemble the system prompt for Pass 2.

    Parameters
    ----------
    db: AsyncSession
        Active database session.
    session_obj: SessionModel
        The session record associated with this chunk.
    chunk_obj: ChunkModel
        The chunk record to be reviewed.

    Returns
    -------
    tuple[str, str]
        A tuple of (system_prompt, user_content).  The user content is
        always an empty string in this implementation.
    """
    # Resolve template path relative to this module
    template_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'pass2_reviewer.txt')
    with open(os.path.abspath(template_path), 'r', encoding='utf-8') as f:
        template = f.read()

    # Retrieve the document associated with this chunk
    result_doc = await db.execute(
        select(DocumentModel).where(DocumentModel.id == chunk_obj.document_id)
    )
    doc = result_doc.scalar_one_or_none()
    if doc is None:
        raise ValueError("Document not found for chunk {0}".format(chunk_obj.id))

    # Derive the human-readable document role.  If the role is 'Other',
    # include the role_label if available.  Otherwise, use the assigned
    # role directly.  If no role is assigned, fall back to the
    # document's format.
    if doc.assigned_role:
        if doc.assigned_role == 'Other' and doc.role_label:
            document_role = f"Other — {doc.role_label}"
        else:
            document_role = doc.assigned_role
    else:
        document_role = doc.format.upper()

    # Determine page range string.  Use the chunk's page_start and
    # page_end.  If page_end is None, show only start.  If both are
    # missing, leave unknown.
    if chunk_obj.page_start is not None and chunk_obj.page_end is not None:
        page_start = str(chunk_obj.page_start)
        page_end = str(chunk_obj.page_end)
    elif chunk_obj.page_start is not None:
        page_start = str(chunk_obj.page_start)
        page_end = str(chunk_obj.page_start)
    else:
        page_start = "?"
        page_end = "?"

    # Study type and draft maturity come from the session
    study_type = session_obj.study_type or ''
    draft_maturity = session_obj.draft_maturity or ''
    # Priority notes: include only if provided; prefix with a label so
    # the model recognises it as contextual metadata.
    priority_notes_line = ''
    if session_obj.priority_notes:
        # Prepend a descriptive label for clarity
        priority_notes_line = f"Priority notes: {session_obj.priority_notes}"

    # Build claim registry.  Query numerical claims for this chunk.
    claim_lines: List[str] = []
    result_claims = await db.execute(
        select(ClaimModel).where(
            ClaimModel.chunk_id == chunk_obj.id,
            ClaimModel.parameter_type.in_(NUMERIC_PARAMETER_TYPES),
        )
    )
    claims = result_claims.scalars().all()
    for claim in claims:
        name = claim.parameter_name or ''
        value = claim.value or ''
        unit = claim.unit or ''
        page = claim.page_number if claim.page_number is not None else '?'
        # Build descriptor: parameter_name: value unit (p.X)
        descriptor = f"{name}: {value} {unit}".strip()
        descriptor = f"{descriptor} (p.{page})"
        claim_lines.append(descriptor)
    # Join claims with newlines or use a placeholder if none
    if claim_lines:
        claim_registry = '\n'.join(claim_lines)
    else:
        claim_registry = 'None'

    # Build conflict lines for this chunk.  Retrieve conflicts where
    # this chunk is one of the conflicting pairs.
    conflict_lines: List[str] = []
    result_conflicts = await db.execute(
        select(ConflictModel).where(
            ConflictModel.session_id == session_obj.id,
            (ConflictModel.chunk_id_a == chunk_obj.id) | (ConflictModel.chunk_id_b == chunk_obj.id),
        )
    )
    conflicts = result_conflicts.scalars().all()
    if conflicts:
        # Build a map from document_id to document name for all documents
        result_docs = await db.execute(
            select(DocumentModel).where(DocumentModel.session_id == session_obj.id)
        )
        doc_map = {d.id: d.original_filename for d in result_docs.scalars().all()}
        for conf in conflicts:
            param = conf.parameter_name
            # Determine whether this chunk is side A or B
            if conf.chunk_id_a == chunk_obj.id:
                value_here = conf.value_a
                other_doc_name = doc_map.get(conf.document_id_b, '?')
                other_page = conf.page_b if conf.page_b is not None else '?'
                other_value = conf.value_b
            else:
                value_here = conf.value_b
                other_doc_name = doc_map.get(conf.document_id_a, '?')
                other_page = conf.page_a if conf.page_a is not None else '?'
                other_value = conf.value_a
            line = (
                f"CONFLICT: \"{param}\" — This document states \"{value_here}\". "
                f"{other_doc_name} (p.{other_page}) states \"{other_value}\". Identify and flag this discrepancy."
            )
            conflict_lines.append(line)
    # Determine conflict block replacement.  If empty, we return an empty string
    conflict_block = '\n'.join(conflict_lines) if conflict_lines else ''

    # Replace placeholders in template
    prompt = template
    prompt = prompt.replace('[DOCUMENT_FILENAME]', doc.original_filename)
    prompt = prompt.replace('[DOCUMENT_ROLE]', document_role)
    prompt = prompt.replace('[PAGE_START]', page_start)
    prompt = prompt.replace('[PAGE_END]', page_end)
    prompt = prompt.replace('[STUDY_TYPE]', study_type)
    prompt = prompt.replace('[DRAFT_MATURITY]', draft_maturity)
    # Replace priority notes line: remove placeholder entirely if not provided
    if priority_notes_line:
        prompt = prompt.replace('[PRIORITY_NOTES_IF_PROVIDED]', priority_notes_line)
    else:
        prompt = prompt.replace('[PRIORITY_NOTES_IF_PROVIDED]\n', '')
        prompt = prompt.replace('[PRIORITY_NOTES_IF_PROVIDED]', '')
    # Replace claim registry placeholder
    prompt = prompt.replace('[LIST OF: parameter_name: value unit (page X)]', claim_registry)
    # Replace conflict list placeholder
    prompt = prompt.replace('[LIST OF: CONFLICT: "[parameter_name]" — This document states "[value_a]". \n[other_document_name] (p.[page_b]) states "[value_b]". Identify and flag this discrepancy.]', conflict_block)
    # If no conflicts, remove the entire conflict block header and marker.  The template
    # includes the header and description preceding the placeholder.  If there are no
    # conflict lines, we simply replace the placeholder with an empty string, leaving
    # the header; this indicates to the model that there are no conflicts.
    # Replace INHAND terms placeholder with empty string (not implemented)
    prompt = prompt.replace('[INHAND_TERMS_FOR_DETECTED_ORGAN_SYSTEMS]', '')
    # Replace chunk text placeholder
    chunk_text = chunk_obj.text_content or ''
    prompt = prompt.replace('[CHUNK_TEXT]', chunk_text)

    # Return final system prompt and an empty user content
    return prompt, ''
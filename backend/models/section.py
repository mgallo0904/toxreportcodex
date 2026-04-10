"""DocumentSection model definition.

Represents a heading extracted from a document during Pass 1. Sections
capture the hierarchical outline of each document and record their
position within the source file. Sections may have a parent to
represent nested headings.
"""

from __future__ import annotations

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class DocumentSection(Base):
    __tablename__ = "document_sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    header_text = Column(String, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_level = Column(Integer, nullable=False, default=1)
    parent_section_id = Column(UUID(as_uuid=True), ForeignKey("document_sections.id"), nullable=True)

    # Relationships
    chunk = relationship("Chunk", back_populates="sections")
    document = relationship("Document")
    session = relationship("Session")
    parent = relationship("DocumentSection", remote_side=[id], backref="children")
"""Document model definition.

Represents an uploaded file within a review session. Documents can be
PDF, DOCX or XLSX files and have an optional assigned role that
determines their function in the review process.
"""

from __future__ import annotations

from sqlalchemy import Column, String, Integer, ForeignKey, CheckConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(String, nullable=False)
    format = Column(String, nullable=False)
    # The assigned role determines the document's function in the review.  See
    # build specification for the list of allowed values.  A check
    # constraint enforces that only recognised roles or NULL may be
    # stored.  Note: Alembic migration must be generated and applied
    # when adding this constraint in a real environment.
    assigned_role = Column(String, nullable=True)
    role_label = Column(String, nullable=True)
    total_pages = Column(Integer, nullable=True)
    total_chunks = Column(Integer, nullable=True)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="document", cascade="all, delete-orphan")
    conflicts_a = relationship(
        "Conflict",
        foreign_keys="Conflict.document_id_a",
        back_populates="document_a",
    )
    conflicts_b = relationship(
        "Conflict",
        foreign_keys="Conflict.document_id_b",
        back_populates="document_b",
    )
    findings = relationship("Finding", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("format IN ('pdf','docx','xlsx')", name="ck_documents_format"),
        CheckConstraint(
            "assigned_role IS NULL OR assigned_role IN (\n"
            "  'Primary Report (Final)',\n"
            "  'Primary Report (Draft)',\n"
            "  'Study Protocol',\n"
            "  'Protocol Amendment',\n"
            "  'Bioanalytical/PK Sub-report',\n"
            "  'Histopathology Sub-report',\n"
            "  'Raw Data Appendix',\n"
            "  'Other'\n"
            ")",
            name="ck_documents_assigned_role",
        ),
    )
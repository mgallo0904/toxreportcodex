"""Initial database schema for the toxicology review agent.

This migration defines all tables required for the application. It is
hand‑written to mirror the schema defined in the specification. In a
development environment the equivalent file would be generated via
`alembic revision --autogenerate -m "initial"`.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum definitions
    study_type_enum = sa.Enum('GLP', 'Non-GLP', name='study_type_enum')
    draft_maturity_enum = sa.Enum('Early Draft', 'Near-Final', 'Final', name='draft_maturity_enum')
    session_status_enum = sa.Enum('uploading', 'roles_assigned', 'mapping', 'section_selection', 'reviewing', 'complete', name='session_status_enum')
    document_format_enum = sa.Enum('pdf', 'docx', 'xlsx', name='document_format_enum')
    pass_status_enum = sa.Enum('pending', 'processing', 'complete', 'error', 'skipped', name='pass_status_enum')
    claim_type_enum = sa.Enum('dose', 'concentration', 'n_count', 'timepoint', 'body_weight', 'organ_weight', 'stat_value', 'abbreviation', 'conclusion', 'method', name='claim_type_enum')
    finding_severity_enum = sa.Enum('Critical', 'Moderate', 'Minor', name='finding_severity_enum')
    confidence_enum = sa.Enum('standard', 'low', name='confidence_enum')
    clarification_status_enum = sa.Enum('pending', 'answered', 'dismissed', name='clarification_status_enum')
    model_provider_enum = sa.Enum('ollama_cloud', 'together_ai', 'custom', name='model_provider_enum')

    # Create enums
    study_type_enum.create(op.get_bind(), checkfirst=True)
    draft_maturity_enum.create(op.get_bind(), checkfirst=True)
    session_status_enum.create(op.get_bind(), checkfirst=True)
    document_format_enum.create(op.get_bind(), checkfirst=True)
    pass_status_enum.create(op.get_bind(), checkfirst=True)
    claim_type_enum.create(op.get_bind(), checkfirst=True)
    finding_severity_enum.create(op.get_bind(), checkfirst=True)
    confidence_enum.create(op.get_bind(), checkfirst=True)
    clarification_status_enum.create(op.get_bind(), checkfirst=True)
    model_provider_enum.create(op.get_bind(), checkfirst=True)

    # Create tables
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('study_name', sa.Text(), nullable=True),
        sa.Column('study_type', study_type_enum, nullable=True),
        sa.Column('draft_maturity', draft_maturity_enum, nullable=True),
        sa.Column('priority_notes', sa.Text(), nullable=True),
        sa.Column('status', session_status_enum, nullable=False, server_default='uploading'),
        sa.Column('active_model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('pass1_started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('pass1_completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('pass2_started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('pass2_completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_filename', sa.Text(), nullable=False),
        sa.Column('format', document_format_enum, nullable=False),
        sa.Column('assigned_role', sa.Text(), nullable=True),
        sa.Column('role_label', sa.Text(), nullable=True),
        sa.Column('total_pages', sa.Integer(), nullable=True),
        sa.Column('total_chunks', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('token_estimate', sa.Integer(), nullable=True),
        sa.Column('pass1_status', pass_status_enum, nullable=False, server_default='pending'),
        sa.Column('pass2_status', pass_status_enum, nullable=False, server_default='pending'),
        sa.Column('pass2_selected', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('pass2_auto_selected', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'document_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('header_text', sa.Text(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('parent_section_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_sections.id'), nullable=True),
    )

    op.create_table(
        'claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parameter_type', claim_type_enum, nullable=False),
        sa.Column('parameter_name', sa.Text(), nullable=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('unit', sa.Text(), nullable=True),
        sa.Column('context_sentence', sa.Text(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'conflicts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parameter_name', sa.Text(), nullable=False),
        sa.Column('value_a', sa.Text(), nullable=True),
        sa.Column('document_id_a', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('chunk_id_a', postgresql.UUID(as_uuid=True), sa.ForeignKey('chunks.id'), nullable=True),
        sa.Column('page_a', sa.Integer(), nullable=True),
        sa.Column('value_b', sa.Text(), nullable=True),
        sa.Column('document_id_b', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('chunk_id_b', postgresql.UUID(as_uuid=True), sa.ForeignKey('chunks.id'), nullable=True),
        sa.Column('page_b', sa.Integer(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'findings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chunks.id'), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('finding_label', sa.Text(), nullable=True),
        sa.Column('page_section_table', sa.Text(), nullable=True),
        sa.Column('original_text', sa.Text(), nullable=True),
        sa.Column('category', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('severity', finding_severity_enum, nullable=True),
        sa.Column('source_reference', sa.Text(), nullable=True),
        sa.Column('confidence', confidence_enum, nullable=False, server_default='standard'),
        sa.Column('confirmed_correct', sa.Boolean(), nullable=True),
        sa.Column('confirmed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_seed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'clarifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chunks.id'), nullable=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('status', clarification_status_enum, nullable=False, server_default='pending'),
        sa.Column('answer_text', sa.Text(), nullable=True),
        sa.Column('answered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'finetune_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('base_model', sa.Text(), nullable=False),
        sa.Column('training_session_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('training_example_count', sa.Integer(), nullable=True),
        sa.Column('lora_rank', sa.Integer(), nullable=False, server_default='16'),
        sa.Column('lora_alpha', sa.Integer(), nullable=False, server_default='32'),
        sa.Column('epochs', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('adapter_path', sa.Text(), nullable=True),
        sa.Column('ollama_model_tag', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='queued'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'model_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('display_name', sa.Text(), nullable=False),
        sa.Column('model_tag', sa.Text(), nullable=False),
        sa.Column('provider', model_provider_enum, nullable=False),
        sa.Column('is_fine_tuned', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('base_model', sa.Text(), nullable=True),
        sa.Column('finetune_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('finetune_jobs.id'), nullable=True),
        sa.Column('context_length', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Add foreign key constraint for sessions.active_model_id referencing model_configs.id
    op.create_foreign_key(
        'fk_sessions_active_model_id_model_configs',
        source_table='sessions',
        referent_table='model_configs',
        local_cols=['active_model_id'],
        remote_cols=['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_sessions_active_model_id_model_configs', 'sessions', type_='foreignkey')

    # Drop tables in reverse order
    op.drop_table('model_configs')
    op.drop_table('finetune_jobs')
    op.drop_table('clarifications')
    op.drop_table('findings')
    op.drop_table('conflicts')
    op.drop_table('claims')
    op.drop_table('document_sections')
    op.drop_table('chunks')
    op.drop_table('documents')
    op.drop_table('sessions')

    # Drop enums
    model_provider_enum = sa.Enum(name='model_provider_enum')
    clarification_status_enum = sa.Enum(name='clarification_status_enum')
    confidence_enum = sa.Enum(name='confidence_enum')
    finding_severity_enum = sa.Enum(name='finding_severity_enum')
    claim_type_enum = sa.Enum(name='claim_type_enum')
    pass_status_enum = sa.Enum(name='pass_status_enum')
    document_format_enum = sa.Enum(name='document_format_enum')
    session_status_enum = sa.Enum(name='session_status_enum')
    draft_maturity_enum = sa.Enum(name='draft_maturity_enum')
    study_type_enum = sa.Enum(name='study_type_enum')
    for enum in [
        model_provider_enum,
        clarification_status_enum,
        confidence_enum,
        finding_severity_enum,
        claim_type_enum,
        pass_status_enum,
        document_format_enum,
        session_status_enum,
        draft_maturity_enum,
        study_type_enum,
    ]:
        enum.drop(op.get_bind(), checkfirst=True)
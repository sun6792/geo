"""P6 Authenticity Upgrade — Alembic migration for raw request/response storage.

Adds fields to llm_probe_results for full traceability:
- raw_request: complete API request body
- raw_response: complete API response JSON
- api_request_id: official request ID for verification
- model_version: actual model version used
- probe_mode: natural_probe / brand_check
- confidence: parsing confidence 0-1
- has_search_source: whether response includes search citations

Also adds diagnosis_rule table for rule-based diagnosis engine.
"""

import sqlalchemy as sa
from alembic import op

# Revision identifiers
revision = 'p6_authenticity_v1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── llm_probe_results: add authenticity fields ────────────
    op.add_column('llm_probe_results', sa.Column('raw_request', sa.JSON(), nullable=True))
    op.add_column('llm_probe_results', sa.Column('raw_response', sa.Text(), nullable=True))
    op.add_column('llm_probe_results', sa.Column('api_request_id', sa.String(128), nullable=True))
    op.add_column('llm_probe_results', sa.Column('model_version', sa.String(64), nullable=True))
    op.add_column('llm_probe_results', sa.Column('probe_mode', sa.String(32), nullable=False, server_default='natural_probe'))
    op.add_column('llm_probe_results', sa.Column('confidence', sa.Float(), nullable=True, server_default='1.0'))
    op.add_column('llm_probe_results', sa.Column('has_search_source', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('llm_probe_results', sa.Column('query_variant_group', sa.String(64), nullable=True))
    op.add_column('llm_probe_results', sa.Column('search_engine_name', sa.String(32), nullable=True))

    # Index for query_variant_group
    op.create_index('idx_llm_probe_variant_group', 'llm_probe_results', ['query_variant_group'])

    # ── diagnosis_rule table ──────────────────────────────────
    op.create_table(
        'diagnosis_rule',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('rule_name', sa.String(200), nullable=False),
        sa.Column('rule_category', sa.String(50), nullable=False),
        sa.Column('condition_json', sa.JSON(), nullable=False),
        sa.Column('problem', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('suggestion', sa.Text(), nullable=False),
        sa.Column('level', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('evidence_field', sa.String(100), nullable=False),
        sa.Column('target_models', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade():
    op.drop_table('diagnosis_rule')
    op.drop_index('idx_llm_probe_variant_group', table_name='llm_probe_results')
    op.drop_column('llm_probe_results', 'search_engine_name')
    op.drop_column('llm_probe_results', 'query_variant_group')
    op.drop_column('llm_probe_results', 'has_search_source')
    op.drop_column('llm_probe_results', 'confidence')
    op.drop_column('llm_probe_results', 'probe_mode')
    op.drop_column('llm_probe_results', 'model_version')
    op.drop_column('llm_probe_results', 'api_request_id')
    op.drop_column('llm_probe_results', 'raw_response')
    op.drop_column('llm_probe_results', 'raw_request')

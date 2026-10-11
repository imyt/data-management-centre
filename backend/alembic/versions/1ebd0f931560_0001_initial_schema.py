"""0001_initial_schema

Revision ID: 1ebd0f931560
Revises: 
Create Date: 2026-10-10 23:10:33.909277

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1ebd0f931560'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Baseline schema for Enterprise Data Management Centre on PostgreSQL 18+."""
    # -------------------------------------------------------------------------
    # 0. PostgreSQL Extensions
    # Native uuidv7() is built into PostgreSQL 18 core (uuid-ossp dropped)
    # -------------------------------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')

    # -------------------------------------------------------------------------
    # 1. Metamodel Engine & Organizational Scoping (Base Tables)
    # -------------------------------------------------------------------------
    op.create_table(
        'asset_types',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_asset_type_id', sa.UUID(), nullable=True),
        sa.Column('is_deprecated', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('icon', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_asset_type_id'], ['asset_types.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    op.create_table(
        'attribute_types',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column(
            'data_type',
            sa.Enum('STRING', 'MARKDOWN', 'NUMBER', 'BOOLEAN', 'DATE', 'ENUM', name='attribute_data_type'),
            server_default='STRING',
            nullable=False
        ),
        sa.Column('allowed_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_deprecated', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    op.create_table(
        'communities',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_community_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_community_id'], ['communities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_communities_parent', 'communities', ['parent_community_id'], unique=False)

    op.create_table(
        'governance_roles',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_superuser', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table(
        'asset_type_attribute_assignments',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('asset_type_id', sa.UUID(), nullable=False),
        sa.Column('attribute_type_id', sa.UUID(), nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('default_value', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.ForeignKeyConstraint(['asset_type_id'], ['asset_types.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attribute_type_id'], ['attribute_types.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_type_id', 'attribute_type_id', name='uq_type_attribute')
    )

    op.create_table(
        'domains',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('community_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'domain_type',
            sa.Enum('GLOSSARY', 'DATA_PRODUCT', 'POLICY', 'SYSTEMS_REGISTER', 'METRIC_STORE', name='domain_type_enum'),
            server_default='GLOSSARY',
            nullable=False
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('community_id', 'name', name='uq_community_domain_name')
    )
    op.create_index('idx_domains_community', 'domains', ['community_id'], unique=False)

    op.create_table(
        'relation_types',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('source_asset_type_id', sa.UUID(), nullable=False),
        sa.Column('target_asset_type_id', sa.UUID(), nullable=False),
        sa.Column('role_name', sa.String(length=100), nullable=False),
        sa.Column('co_role_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_deprecated', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_asset_type_id'], ['asset_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_asset_type_id'], ['asset_types.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    op.create_table(
        'workflow_definitions',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('asset_type_id', sa.UUID(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_type_id'], ['asset_types.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'workflow_stages',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('workflow_definition_id', sa.UUID(), nullable=False),
        sa.Column('stage_order', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('required_role', sa.String(length=50), nullable=False),
        sa.Column('is_consensus', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('sla_hours', sa.Integer(), server_default=sa.text('48'), nullable=False),
        sa.ForeignKeyConstraint(['workflow_definition_id'], ['workflow_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_definition_id', 'stage_order', name='uq_definition_stage_order')
    )

    # -------------------------------------------------------------------------
    # 2. Asset Heads, Versions & Relations
    # -------------------------------------------------------------------------
    op.create_table(
        'asset_heads',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('domain_id', sa.UUID(), nullable=False),
        sa.Column('asset_type_id', sa.UUID(), nullable=False),
        sa.Column('published_version_id', sa.UUID(), nullable=True),
        sa.Column('active_draft_version_id', sa.UUID(), nullable=True),
        sa.Column('locked_by_user_id', sa.UUID(), nullable=True),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_type_id'], ['asset_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['locked_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_asset_heads_domain', 'asset_heads', ['domain_id'], unique=False)
    op.create_index('idx_asset_heads_type', 'asset_heads', ['asset_type_id'], unique=False)

    op.create_table(
        'asset_versions',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('asset_head_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'UNDER_REVIEW', 'PUBLISHED', 'SUPERSEDED', 'REJECTED', 'DEPRECATED', name='version_status_enum'),
            server_default='DRAFT',
            nullable=False
        ),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description_markdown', sa.Text(), nullable=True),
        sa.Column('attributes_payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('relations_snapshot', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['asset_head_id'], ['asset_heads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_head_id', 'version_number', name='uq_head_version')
    )
    op.create_index(
        'idx_asset_versions_name_trgm',
        'asset_versions',
        ['name'],
        unique=False,
        postgresql_using='gin',
        postgresql_ops={'name': 'gin_trgm_ops'}
    )

    # Circular Foreign Key Constraints on asset_heads pointing to asset_versions
    op.create_foreign_key(
        'fk_head_published_version',
        'asset_heads',
        'asset_versions',
        ['published_version_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_head_draft_version',
        'asset_heads',
        'asset_versions',
        ['active_draft_version_id'],
        ['id'],
        ondelete='SET NULL'
    )

    op.create_table(
        'asset_relations',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('relation_type_id', sa.UUID(), nullable=False),
        sa.Column('source_asset_head_id', sa.UUID(), nullable=False),
        sa.Column('target_asset_head_id', sa.UUID(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('source_asset_head_id <> target_asset_head_id', name='ck_no_self_relation'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['relation_type_id'], ['relation_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['source_asset_head_id'], ['asset_heads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_asset_head_id'], ['asset_heads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('relation_type_id', 'source_asset_head_id', 'target_asset_head_id', name='uq_source_target_relation')
    )
    op.create_index('idx_relations_source', 'asset_relations', ['source_asset_head_id'], unique=False)
    op.create_index('idx_relations_target', 'asset_relations', ['target_asset_head_id'], unique=False)

    # -------------------------------------------------------------------------
    # 3. RACI Roles & Scoped Responsibilities
    # -------------------------------------------------------------------------
    op.create_table(
        'responsibility_assignments',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('community_id', sa.UUID(), nullable=True),
        sa.Column('domain_id', sa.UUID(), nullable=True),
        sa.Column('asset_head_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            '(community_id IS NOT NULL AND domain_id IS NULL AND asset_head_id IS NULL) OR '
            '(community_id IS NULL AND domain_id IS NOT NULL AND asset_head_id IS NULL) OR '
            '(community_id IS NULL AND domain_id IS NULL AND asset_head_id IS NOT NULL)',
            name='ck_single_assignment_scope'
        ),
        sa.ForeignKeyConstraint(['asset_head_id'], ['asset_heads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['governance_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_resp_asset', 'responsibility_assignments', ['asset_head_id'], unique=False)
    op.create_index('idx_resp_comm', 'responsibility_assignments', ['community_id'], unique=False)
    op.create_index('idx_resp_domain', 'responsibility_assignments', ['domain_id'], unique=False)

    # -------------------------------------------------------------------------
    # 4. Multi-Stage Workflow Engine Instances & Tasks
    # -------------------------------------------------------------------------
    op.create_table(
        'workflow_instances',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('workflow_definition_id', sa.UUID(), nullable=False),
        sa.Column('asset_version_id', sa.UUID(), nullable=False),
        sa.Column('current_stage_order', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column(
            'status',
            sa.Enum('RUNNING', 'COMPLETED', 'REJECTED', 'CANCELLED', name='workflow_instance_status'),
            server_default='RUNNING',
            nullable=False
        ),
        sa.Column('initiated_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['asset_version_id'], ['asset_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['initiated_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['workflow_definition_id'], ['workflow_definitions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'stage_approval_tasks',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('workflow_instance_id', sa.UUID(), nullable=False),
        sa.Column('stage_id', sa.UUID(), nullable=False),
        sa.Column('assigned_user_id', sa.UUID(), nullable=True),
        sa.Column('assigned_role', sa.String(length=50), nullable=False),
        sa.Column(
            'decision',
            sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'CHANGES_REQUESTED', name='task_decision_enum'),
            server_default='PENDING',
            nullable=False
        ),
        sa.Column('decision_notes', sa.Text(), nullable=True),
        sa.Column('decided_by', sa.UUID(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['stage_id'], ['workflow_stages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_instance_id'], ['workflow_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'idx_tasks_pending',
        'stage_approval_tasks',
        ['decision'],
        unique=False,
        postgresql_where=sa.text("decision = 'PENDING'")
    )

    # -------------------------------------------------------------------------
    # 5. Compliance Issues & Self-Service Remediation
    # -------------------------------------------------------------------------
    op.create_table(
        'compliance_issues',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('target_asset_head_id', sa.UUID(), nullable=False),
        sa.Column('app_owner_id', sa.UUID(), nullable=False),
        sa.Column('assigned_steward_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column(
            'severity',
            sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='issue_severity_enum'),
            server_default='MEDIUM',
            nullable=False
        ),
        sa.Column(
            'status',
            sa.Enum('OPEN', 'IN_REMEDIATION', 'PENDING_VERIFICATION', 'RESOLVED', 'EXCEPTION_GRANTED', name='issue_status_enum'),
            server_default='OPEN',
            nullable=False
        ),
        sa.Column('remediation_deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['app_owner_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['assigned_steward_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_asset_head_id'], ['asset_heads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_issues_app_owner', 'compliance_issues', ['app_owner_id'], unique=False)
    op.create_index('idx_issues_status', 'compliance_issues', ['status'], unique=False)

    op.create_table(
        'remediation_submissions',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column('submitted_by', sa.UUID(), nullable=False),
        sa.Column('remediation_summary', sa.Text(), nullable=False),
        sa.Column('evidence_urls', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('verified_by', sa.UUID(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('steward_feedback', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['issue_id'], ['compliance_issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submitted_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'compliance_issue_events',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column(
            'from_status',
            sa.Enum('OPEN', 'IN_REMEDIATION', 'PENDING_VERIFICATION', 'RESOLVED', 'EXCEPTION_GRANTED', name='issue_status_enum', create_type=False),
            nullable=True
        ),
        sa.Column(
            'to_status',
            sa.Enum('OPEN', 'IN_REMEDIATION', 'PENDING_VERIFICATION', 'RESOLVED', 'EXCEPTION_GRANTED', name='issue_status_enum', create_type=False),
            nullable=True
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['issue_id'], ['compliance_issues.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop in reverse topological order
    op.drop_table('compliance_issue_events')
    op.drop_table('remediation_submissions')
    op.drop_index('idx_issues_status', table_name='compliance_issues')
    op.drop_index('idx_issues_app_owner', table_name='compliance_issues')
    op.drop_table('compliance_issues')
    
    op.drop_index('idx_tasks_pending', table_name='stage_approval_tasks', postgresql_where=sa.text("decision = 'PENDING'"))
    op.drop_table('stage_approval_tasks')
    op.drop_table('workflow_instances')

    op.drop_index('idx_resp_domain', table_name='responsibility_assignments')
    op.drop_index('idx_resp_comm', table_name='responsibility_assignments')
    op.drop_index('idx_resp_asset', table_name='responsibility_assignments')
    op.drop_table('responsibility_assignments')

    op.drop_index('idx_relations_target', table_name='asset_relations')
    op.drop_index('idx_relations_source', table_name='asset_relations')
    op.drop_table('asset_relations')

    op.drop_constraint('fk_head_draft_version', 'asset_heads', type_='foreignkey')
    op.drop_constraint('fk_head_published_version', 'asset_heads', type_='foreignkey')

    op.drop_index('idx_asset_versions_name_trgm', table_name='asset_versions', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.drop_table('asset_versions')

    op.drop_index('idx_asset_heads_type', table_name='asset_heads')
    op.drop_index('idx_asset_heads_domain', table_name='asset_heads')
    op.drop_table('asset_heads')

    op.drop_table('workflow_stages')
    op.drop_table('workflow_definitions')
    op.drop_table('relation_types')

    op.drop_index('idx_domains_community', table_name='domains')
    op.drop_table('domains')

    op.drop_table('asset_type_attribute_assignments')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('governance_roles')

    op.drop_index('idx_communities_parent', table_name='communities')
    op.drop_table('communities')

    op.drop_table('attribute_types')
    op.drop_table('asset_types')

    # Drop custom PostgreSQL ENUM types
    op.execute("DROP TYPE IF EXISTS issue_status_enum;")
    op.execute("DROP TYPE IF EXISTS issue_severity_enum;")
    op.execute("DROP TYPE IF EXISTS task_decision_enum;")
    op.execute("DROP TYPE IF EXISTS workflow_instance_status;")
    op.execute("DROP TYPE IF EXISTS version_status_enum;")
    op.execute("DROP TYPE IF EXISTS domain_type_enum;")
    op.execute("DROP TYPE IF EXISTS attribute_data_type;")

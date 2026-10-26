"""0001 initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-05 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Accounts
    op.create_table(
        'accounts',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('holder_name_encrypted', sa.Text(), nullable=False),
        sa.Column('account_type', sa.String(32), nullable=False, server_default='personal'),
        sa.Column('risk_tier', sa.String(16), nullable=False, server_default='low'),
        sa.Column('status', sa.String(16), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 2. Devices
    op.create_table(
        'devices',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('device_fingerprint', sa.String(128), nullable=False, unique=True),
        sa.Column('os', sa.String(32), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 3. IPs
    op.create_table(
        'ips',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('ip_address', sa.String(45), nullable=False, unique=True),
        sa.Column('country', sa.String(8), nullable=True),
        sa.Column('is_vpn', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 4. Merchants
    op.create_table(
        'merchants',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('mcc', sa.String(16), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 5. Entity Edges
    op.create_table(
        'entity_edges',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('source_id', sa.String(64), nullable=False),
        sa.Column('source_type', sa.String(32), nullable=False),
        sa.Column('target_id', sa.String(64), nullable=False),
        sa.Column('target_type', sa.String(32), nullable=False),
        sa.Column('edge_type', sa.String(32), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('idx_entity_edges_source', 'entity_edges', ['source_id', 'source_type'])
    op.create_index('idx_entity_edges_target', 'entity_edges', ['target_id', 'target_type'])

    # 6. Transactions
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_account_id', sa.String(64), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('target_account_id', sa.String(64), sa.ForeignKey('accounts.id'), nullable=True),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(8), nullable=False, server_default='USD'),
        sa.Column('channel', sa.String(32), nullable=False, server_default='mobile_app'),
        sa.Column('device_id', sa.String(64), sa.ForeignKey('devices.id'), nullable=True),
        sa.Column('ip_id', sa.String(64), sa.ForeignKey('ips.id'), nullable=True),
        sa.Column('merchant_id', sa.String(64), sa.ForeignKey('merchants.id'), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('idx_transactions_source_acct', 'transactions', ['source_account_id', 'timestamp'])
    op.create_index('idx_transactions_target_acct', 'transactions', ['target_account_id', 'timestamp'])

    # 7. Decisions
    op.create_table(
        'decisions',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('transaction_id', sa.String(64), sa.ForeignKey('transactions.id'), nullable=False, unique=True),
        sa.Column('decision', sa.String(16), nullable=False), # APPROVE, REVIEW, DECLINE
        sa.Column('probability', sa.Float(), nullable=False),
        sa.Column('rule_hits', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('reason_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.Column('model_version', sa.String(64), nullable=False),
        sa.Column('degraded', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 8. Alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('alert_id', sa.String(64), nullable=False, unique=True),
        sa.Column('transaction_id', sa.String(64), sa.ForeignKey('transactions.id'), nullable=False),
        sa.Column('alert_type', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False, server_default='medium'),
        sa.Column('case_id', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 9. Cases
    op.create_table(
        'cases',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('case_id', sa.String(64), nullable=False, unique=True),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('priority', sa.String(16), nullable=False, server_default='medium'), # low, medium, high, critical
        sa.Column('status', sa.String(32), nullable=False, server_default='open'), # open, investigating, pending_review, closed
        sa.Column('assigned_analyst', sa.String(128), nullable=True),
        sa.Column('sla_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 10. Evidence Items
    op.create_table(
        'evidence_items',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('case_id', sa.String(64), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('kind', sa.String(64), nullable=False), # graph_finding, pattern_finding, media_article, analyst_note
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('source_ref', sa.String(256), nullable=True),
        sa.Column('created_by', sa.String(64), nullable=False), # agent name or analyst user_id
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 11. SAR Drafts
    op.create_table(
        'sar_drafts',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('case_id', sa.String(64), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('narrative_md', sa.Text(), nullable=False),
        sa.Column('citations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('status', sa.String(32), nullable=False, server_default='draft'), # draft, edited, approved, rejected
        sa.Column('author', sa.String(64), nullable=False), # NarrativeWriter agent or analyst
        sa.Column('reviewed_by', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 12. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('username', sa.String(64), nullable=False, unique=True),
        sa.Column('email', sa.String(128), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(256), nullable=False),
        sa.Column('role', sa.String(32), nullable=False), # fraud_analyst, aml_analyst, manager, admin
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 13. Audit Log
    op.create_table(
        'audit_log',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('actor', sa.String(128), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 14. Ground Truth Labels (Isolated from serving model)
    op.create_table(
        'ground_truth_labels',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('transaction_id', sa.String(64), sa.ForeignKey('transactions.id'), nullable=False, unique=True),
        sa.Column('is_fraud', sa.Boolean(), nullable=False),
        sa.Column('typology_type', sa.String(64), nullable=True), # smurfing, layering, round_tripping, fraud_ring, normal
        sa.Column('injected_pattern', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 15. Sanctions List
    op.create_table(
        'sanctions_list',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('entity_name', sa.String(128), nullable=False),
        sa.Column('entity_type', sa.String(32), nullable=False), # individual, company, bank
        sa.Column('country', sa.String(8), nullable=True),
        sa.Column('listed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('sanctions_list')
    op.drop_table('ground_truth_labels')
    op.drop_table('audit_log')
    op.drop_table('users')
    op.drop_table('sar_drafts')
    op.drop_table('evidence_items')
    op.drop_table('cases')
    op.drop_table('alerts')
    op.drop_table('decisions')
    op.drop_table('transactions')
    op.drop_table('entity_edges')
    op.drop_table('merchants')
    op.drop_table('ips')
    op.drop_table('devices')
    op.drop_table('accounts')

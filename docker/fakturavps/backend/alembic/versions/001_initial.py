"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    op.create_table('companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('nip', sa.String(20), nullable=False),
        sa.Column('regon', sa.String(20), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('postal_code', sa.String(10), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('bank_account', sa.String(50), nullable=True),
        sa.Column('vat_rate_default', sa.Integer(), nullable=False, server_default='23'),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(30), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('contractors',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nip', sa.String(20), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('regon', sa.String(20), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('postal_code', sa.String(10), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(30), nullable=True),
        sa.Column('bank_account', sa.String(50), nullable=True),
        sa.Column('default_payment_days', sa.Integer(), nullable=False, server_default='14'),
        sa.Column('category', sa.String(20), nullable=False, server_default='klient'),
        sa.Column('status', sa.String(20), nullable=False, server_default='aktywny'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('number', sa.String(50), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('contractor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('sale_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='szkic'),
        sa.Column('net_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('vat_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('gross_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='PLN'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('ksef_reference_number', sa.String(100), nullable=True),
        sa.Column('ksef_number', sa.String(100), nullable=True),
        sa.Column('upo_xml', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('number')
    )

    op.create_table('invoice_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 4), nullable=False),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('unit_price_net', sa.Numeric(12, 4), nullable=False),
        sa.Column('vat_rate', sa.String(5), nullable=False),
        sa.Column('net_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('vat_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('gross_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('position_order', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('invoice_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_status', sa.String(30), nullable=True),
        sa.Column('new_status', sa.String(30), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('changed_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source', sa.String(20), nullable=False, server_default='user'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('method', sa.String(20), nullable=False, server_default='przelew'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=True),
        sa.Column('old_data', postgresql.JSON(), nullable=True),
        sa.Column('new_data', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_invoices_number', 'invoices', ['number'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])
    op.create_index('ix_invoices_contractor_id', 'invoices', ['contractor_id'])
    op.create_index('ix_contractors_nip', 'contractors', ['nip'])
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('payments')
    op.drop_table('invoice_status_history')
    op.drop_table('invoice_items')
    op.drop_table('invoices')
    op.drop_table('contractors')
    op.drop_table('companies')
    op.drop_table('users')

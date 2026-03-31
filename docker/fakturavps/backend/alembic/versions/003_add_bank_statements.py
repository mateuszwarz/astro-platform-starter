"""Add bank_statements and bank_transactions tables

Revision ID: 003
Revises: 002
Create Date: 2026-03-31 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('bank_statements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('stored_path', sa.String(500), nullable=True),
        sa.Column('bank_name', sa.String(100), nullable=True),
        sa.Column('account_number', sa.String(50), nullable=True),
        sa.Column('statement_date_from', sa.Date(), nullable=True),
        sa.Column('statement_date_to', sa.Date(), nullable=True),
        sa.Column('transaction_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('matched_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('uploaded_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('bank_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('statement_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('booking_date', sa.Date(), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='PLN'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('counterparty_name', sa.String(255), nullable=True),
        sa.Column('counterparty_account', sa.String(50), nullable=True),
        sa.Column('reference', sa.String(100), nullable=True),
        sa.Column('match_status', sa.String(20), nullable=False, server_default='unmatched'),
        sa.Column('matched_invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('match_confidence', sa.Integer(), nullable=True),
        sa.Column('match_notes', sa.Text(), nullable=True),
        sa.Column('matched_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('matched_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['statement_id'], ['bank_statements.id']),
        sa.ForeignKeyConstraint(['matched_invoice_id'], ['invoices.id']),
        sa.ForeignKeyConstraint(['matched_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bank_transactions_match_status', 'bank_transactions', ['match_status'])
    op.create_index('ix_bank_transactions_statement_id', 'bank_transactions', ['statement_id'])


def downgrade() -> None:
    op.drop_table('bank_transactions')
    op.drop_table('bank_statements')

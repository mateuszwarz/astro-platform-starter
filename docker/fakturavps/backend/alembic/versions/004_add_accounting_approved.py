"""Add accounting_approved to invoices

Revision ID: 004
Revises: 003
Create Date: 2026-03-31 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'invoices',
        sa.Column('accounting_approved', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    op.drop_column('invoices', 'accounting_approved')

"""Add cost_type and attachment fields to invoices

Revision ID: 002
Revises: 001
Create Date: 2026-03-31 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('invoices', sa.Column('cost_type', sa.String(10), nullable=True))
    op.add_column('invoices', sa.Column('attachment_path', sa.String(500), nullable=True))
    op.add_column('invoices', sa.Column('attachment_filename', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('invoices', 'attachment_filename')
    op.drop_column('invoices', 'attachment_path')
    op.drop_column('invoices', 'cost_type')

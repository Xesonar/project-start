"""public portfolio slug

Revision ID: e7b2c9d5f130
Revises: 36c4c53fa224
Create Date: 2026-09-24 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7b2c9d5f130'
down_revision: Union[str, None] = '36c4c53fa224'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('portfolio_slug', sa.String(length=64), nullable=True),
    )
    op.create_index(
        'ix_users_portfolio_slug',
        'users',
        ['portfolio_slug'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_users_portfolio_slug', table_name='users')
    op.drop_column('users', 'portfolio_slug')

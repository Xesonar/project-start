"""add withdrawn application status

Revision ID: b6e8f1a2c3d4
Revises: f4a1b2c3d4e5
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b6e8f1a2c3d4"
down_revision: Union[str, None] = "f4a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL requires a commit before a newly added enum value may be used
    # by later migrations in the same `alembic upgrade head` run.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE application_status ADD VALUE IF NOT EXISTS 'withdrawn'")


def downgrade() -> None:
    # PostgreSQL cannot remove an enum value safely while rows may use it.
    pass

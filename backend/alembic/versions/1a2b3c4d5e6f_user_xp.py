"""add verified-experience XP

Revision ID: 1a2b3c4d5e6f
Revises: 0f1a2b3c4d5e
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "0f1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("xp", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("users", "xp")

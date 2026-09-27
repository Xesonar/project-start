"""add project communication flow

Revision ID: c7f9a2b3d4e5
Revises: b6e8f1a2c3d4
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c7f9a2b3d4e5"
down_revision: Union[str, None] = "b6e8f1a2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE application_status ADD VALUE IF NOT EXISTS 'leave_requested'")
    op.add_column("applications", sa.Column("decision_note", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("team_chat_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "team_chat_url")
    op.drop_column("applications", "decision_note")

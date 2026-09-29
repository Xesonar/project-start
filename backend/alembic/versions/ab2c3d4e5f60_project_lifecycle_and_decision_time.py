"""separate recruitment closure from project work

Revision ID: ab2c3d4e5f60
Revises: fa1b2c3d4e5f
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ab2c3d4e5f60"
down_revision: Union[str, None] = "fa1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'recruitment_closed' AFTER 'open'")
    op.add_column(
        "applications",
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE applications SET decided_at = created_at "
        "WHERE status IN ('accepted', 'rejected')"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE projects SET status = 'in_progress' "
        "WHERE status = 'recruitment_closed'"
    )
    op.drop_column("applications", "decided_at")

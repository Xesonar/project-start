"""add project submissions

Revision ID: d8a1b2c3d4e5
Revises: c7f9a2b3d4e5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d8a1b2c3d4e5"
down_revision: Union[str, None] = "c7f9a2b3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    submission_status = postgresql.ENUM(
        "submitted",
        "revision_requested",
        "approved",
        "rejected",
        name="project_submission_status",
        create_type=False,
    )
    submission_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "project_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("result_url", sa.String(length=1024), nullable=True),
        sa.Column("status", submission_status, nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_submission_project_user"),
    )


def downgrade() -> None:
    op.drop_table("project_submissions")
    postgresql.ENUM(name="project_submission_status").drop(op.get_bind(), checkfirst=True)

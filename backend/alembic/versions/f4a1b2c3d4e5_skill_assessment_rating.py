"""five-step skill self-assessment rating

Revision ID: f4a1b2c3d4e5
Revises: e7b2c9d5f130
Create Date: 2026-09-25 12:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a1b2c3d4e5"
down_revision: Union[str, None] = "e7b2c9d5f130"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_skills",
        sa.Column("rating", sa.SmallInteger(), nullable=False, server_default="2"),
    )
    op.execute("UPDATE user_skills SET rating = 3 WHERE level = 'intermediate'")
    op.execute("UPDATE user_skills SET rating = 4 WHERE level = 'advanced'")
    op.alter_column("user_skills", "rating", server_default=None)
    op.create_check_constraint(
        "ck_user_skills_rating_range", "user_skills", "rating BETWEEN 1 AND 4"
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_skills_rating_range", "user_skills", type_="check")
    op.drop_column("user_skills", "rating")

"""mark demo users and projects

Revision ID: e9f1a2b3c4d5
Revises: d8a1b2c3d4e5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e9f1a2b3c4d5"
down_revision: Union[str, None] = "d8a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(op.f("ix_users_is_demo"), "users", ["is_demo"], unique=False)
    op.add_column(
        "projects",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(op.f("ix_projects_is_demo"), "projects", ["is_demo"], unique=False)

    op.execute(sa.text("UPDATE users SET is_demo = true WHERE max_user_id < 0"))
    op.execute(
        sa.text(
            "UPDATE projects SET is_demo = true "
            "WHERE title = 'Демо: навигатор по мероприятиям университета'"
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_projects_is_demo"), table_name="projects")
    op.drop_column("projects", "is_demo")
    op.drop_index(op.f("ix_users_is_demo"), table_name="users")
    op.drop_column("users", "is_demo")

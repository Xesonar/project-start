"""remove demo mode, preserve application history, add MAX outbox

Revision ID: fa1b2c3d4e5f
Revises: e9f1a2b3c4d5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "fa1b2c3d4e5f"
down_revision: Union[str, None] = "e9f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove synthetic records before dropping their marker columns. Real MAX
    # users always have a positive max_user_id, so this is deterministic.
    op.execute("DELETE FROM projects WHERE is_demo = true")
    op.execute("DELETE FROM users WHERE is_demo = true OR max_user_id < 0")

    op.drop_index(op.f("ix_projects_is_demo"), table_name="projects")
    op.drop_column("projects", "is_demo")
    op.drop_index(op.f("ix_users_is_demo"), table_name="users")
    op.drop_column("users", "is_demo")

    op.drop_constraint("uq_application_role", "applications", type_="unique")
    op.create_index(
        "uq_application_active_role",
        "applications",
        ["user_id", "project_id", "project_role_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('pending', 'accepted', 'leave_requested')"
        ),
    )

    op.create_table(
        "bot_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("buttons", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_bot_notifications_user_id", "bot_notifications", ["user_id"])
    op.create_index("ix_bot_notifications_status", "bot_notifications", ["status"])
    op.create_index("ix_bot_notifications_next_attempt_at", "bot_notifications", ["next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_bot_notifications_next_attempt_at", table_name="bot_notifications")
    op.drop_index("ix_bot_notifications_status", table_name="bot_notifications")
    op.drop_index("ix_bot_notifications_user_id", table_name="bot_notifications")
    op.drop_table("bot_notifications")

    op.drop_index("uq_application_active_role", table_name="applications")
    # Downgrade keeps the newest application per role so the historical unique
    # constraint can be restored without failing.
    op.execute(
        "DELETE FROM applications older USING applications newer "
        "WHERE older.user_id = newer.user_id "
        "AND older.project_id = newer.project_id "
        "AND older.project_role_id = newer.project_role_id "
        "AND older.id < newer.id"
    )
    op.create_unique_constraint(
        "uq_application_role",
        "applications",
        ["user_id", "project_id", "project_role_id"],
    )

    op.add_column("users", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_users_is_demo"), "users", ["is_demo"])
    op.add_column("projects", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_projects_is_demo"), "projects", ["is_demo"])

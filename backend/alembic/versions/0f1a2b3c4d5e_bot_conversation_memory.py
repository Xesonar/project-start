"""add bounded MAX bot conversation memory

Revision ID: 0f1a2b3c4d5e
Revises: ab2c3d4e5f60
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0f1a2b3c4d5e"
down_revision: Union[str, None] = "ab2c3d4e5f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_key", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("sender_max_user_id", sa.BigInteger(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_bot_conversation_scope_created",
        "bot_conversation_messages",
        ["conversation_key", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bot_conversation_scope_created", table_name="bot_conversation_messages")
    op.drop_table("bot_conversation_messages")

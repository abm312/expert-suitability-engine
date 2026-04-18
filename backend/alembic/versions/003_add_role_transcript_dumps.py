"""Add role transcript dumps table

Revision ID: 003
Revises: 002
Create Date: 2026-04-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "role_transcript_dumps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_slug", sa.String(length=255), nullable=False),
        sa.Column("role_query", sa.String(length=255), nullable=False),
        sa.Column("search_query_used", sa.String(length=255), nullable=False),
        sa.Column("channel_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transcript_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dump_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("refreshed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        "ix_role_transcript_dumps_role_slug",
        "role_transcript_dumps",
        ["role_slug"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_role_transcript_dumps_role_slug", table_name="role_transcript_dumps")
    op.drop_table("role_transcript_dumps")

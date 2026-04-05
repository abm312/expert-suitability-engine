"""Add rising voices table

Revision ID: 002
Revises: 001
Create Date: 2026-04-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rising_voices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("subscriber_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("growth_signal", sa.String(length=255), nullable=False),
        sa.Column("credibility_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("topic_authority_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("communication_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("growth_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("channel_url", sa.String(length=500), nullable=False),
        sa.Column("last_scored", sa.Date(), nullable=False),
        sa.Column("matched_queries", sa.JSON(), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_rising_voices_rank", "rising_voices", ["rank"], unique=False)
    op.create_index("ix_rising_voices_channel_id", "rising_voices", ["channel_id"], unique=True)
    op.create_index("ix_rising_voices_slug", "rising_voices", ["slug"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rising_voices_slug", table_name="rising_voices")
    op.drop_index("ix_rising_voices_channel_id", table_name="rising_voices")
    op.drop_index("ix_rising_voices_rank", table_name="rising_voices")
    op.drop_table("rising_voices")

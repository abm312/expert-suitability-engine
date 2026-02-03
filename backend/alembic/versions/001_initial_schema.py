"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create creators table
    op.create_table(
        'creators',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('channel_name', sa.String(255), nullable=False),
        sa.Column('channel_description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('total_subscribers', sa.BigInteger(), default=0),
        sa.Column('total_views', sa.BigInteger(), default=0),
        sa.Column('total_videos', sa.Integer(), default=0),
        sa.Column('channel_created_date', sa.DateTime(), nullable=True),
        sa.Column('external_links', sa.JSON(), default=list),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('country', sa.String(50), nullable=True),
        sa.Column('last_fetched_at', sa.DateTime(), nullable=True),
        sa.Column('credibility_score', sa.Float(), nullable=True),
        sa.Column('topic_score', sa.Float(), nullable=True),
        sa.Column('communication_score', sa.Float(), nullable=True),
        sa.Column('freshness_score', sa.Float(), nullable=True),
        sa.Column('growth_score', sa.Float(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
    )
    
    # Create videos table
    op.create_table(
        'videos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('creator_id', sa.Integer(), sa.ForeignKey('creators.id', ondelete='CASCADE'), nullable=False),
        sa.Column('video_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), default=0),
        sa.Column('views', sa.BigInteger(), default=0),
        sa.Column('likes', sa.BigInteger(), default=0),
        sa.Column('comments', sa.BigInteger(), default=0),
        sa.Column('has_captions', sa.Boolean(), default=False),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('tags', sa.JSON(), default=list),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Create transcripts table
    op.create_table(
        'transcripts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('video_id', sa.Integer(), sa.ForeignKey('videos.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('language', sa.String(10), default='en'),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Create metrics_snapshots table
    op.create_table(
        'metrics_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('creator_id', sa.Integer(), sa.ForeignKey('creators.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('subscriber_count', sa.BigInteger(), default=0),
        sa.Column('view_count', sa.BigInteger(), default=0),
        sa.Column('video_count', sa.Integer(), default=0),
    )
    
    # Create search_queries table
    op.create_table(
        'search_queries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('query_text', sa.String(500), nullable=False),
        sa.Column('topic_embedding', Vector(1536), nullable=True),
        sa.Column('filters', sa.JSON(), default=dict),
        sa.Column('weights', sa.JSON(), default=dict),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('results_count', sa.Integer(), default=0),
    )
    
    # Create indexes
    op.create_index('idx_videos_creator_id', 'videos', ['creator_id'])
    op.create_index('idx_videos_published_at', 'videos', ['published_at'])
    op.create_index('idx_metrics_creator_date', 'metrics_snapshots', ['creator_id', 'date'])


def downgrade() -> None:
    op.drop_table('search_queries')
    op.drop_table('metrics_snapshots')
    op.drop_table('transcripts')
    op.drop_table('videos')
    op.drop_table('creators')
    op.execute('DROP EXTENSION IF EXISTS vector')


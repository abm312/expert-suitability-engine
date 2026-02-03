from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON, BigInteger, Date
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
from app.db.database import Base
from app.core.config import get_settings

settings = get_settings()


class Creator(Base):
    __tablename__ = "creators"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(50), unique=True, nullable=False, index=True)
    channel_name = Column(String(255), nullable=False)
    channel_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    total_subscribers = Column(BigInteger, default=0)
    total_views = Column(BigInteger, default=0)
    total_videos = Column(Integer, default=0)
    channel_created_date = Column(DateTime, nullable=True)
    external_links = Column(JSON, default=list)
    thumbnail_url = Column(String(500), nullable=True)
    country = Column(String(50), nullable=True)
    last_fetched_at = Column(DateTime, nullable=True)
    
    # Cached scores
    credibility_score = Column(Float, nullable=True)
    topic_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)
    freshness_score = Column(Float, nullable=True)
    growth_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    
    # Relationships
    videos = relationship("Video", back_populates="creator", cascade="all, delete-orphan")
    metrics_snapshots = relationship("MetricsSnapshot", back_populates="creator", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    views = Column(BigInteger, default=0)
    likes = Column(BigInteger, default=0)
    comments = Column(BigInteger, default=0)
    has_captions = Column(Boolean, default=False)
    thumbnail_url = Column(String(500), nullable=True)
    tags = Column(JSON, default=list)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = relationship("Creator", back_populates="videos")
    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), unique=True, nullable=False)
    text = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="transcript")


class MetricsSnapshot(Base):
    __tablename__ = "metrics_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    subscriber_count = Column(BigInteger, default=0)
    view_count = Column(BigInteger, default=0)
    video_count = Column(Integer, default=0)
    
    # Relationships
    creator = relationship("Creator", back_populates="metrics_snapshots")
    
    class Meta:
        unique_together = ("creator_id", "date")


class SearchQuery(Base):
    """Store search queries for analytics and caching"""
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(String(500), nullable=False)
    topic_embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)
    filters = Column(JSON, default=dict)
    weights = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    results_count = Column(Integer, default=0)


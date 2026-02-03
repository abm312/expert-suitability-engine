from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreatorBase(BaseModel):
    channel_id: str
    channel_name: str
    channel_description: Optional[str] = None
    total_subscribers: int = 0
    total_views: int = 0
    total_videos: int = 0
    channel_created_date: Optional[datetime] = None
    external_links: List[str] = []
    thumbnail_url: Optional[str] = None
    country: Optional[str] = None


class CreatorCreate(BaseModel):
    channel_id: str


class CreatorScores(BaseModel):
    credibility_score: Optional[float] = None
    topic_score: Optional[float] = None
    communication_score: Optional[float] = None
    freshness_score: Optional[float] = None
    growth_score: Optional[float] = None
    overall_score: Optional[float] = None


class CreatorResponse(CreatorBase, CreatorScores):
    id: int
    created_at: datetime
    last_fetched_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class VideoSummary(BaseModel):
    video_id: str
    title: str
    published_at: Optional[datetime]
    views: int
    duration_seconds: int
    has_captions: bool
    thumbnail_url: Optional[str] = None


class CreatorDetail(CreatorResponse):
    videos: List[VideoSummary] = []
    growth_data: List[dict] = []
    topic_matches: List[dict] = []
    why_expert: List[str] = []
    suggested_topics: List[str] = []


class CreatorCard(BaseModel):
    """The core output for the UI - a ranked creator card"""
    id: int
    channel_id: str
    channel_name: str
    thumbnail_url: Optional[str]
    total_subscribers: int
    total_views: int
    
    # Scores
    overall_score: float
    subscores: dict
    
    # Explainability
    why_expert: List[str]
    topic_match_summary: str
    top_videos: List[VideoSummary]
    growth_trend: str
    
    # Links
    external_links: List[str]
    channel_url: str


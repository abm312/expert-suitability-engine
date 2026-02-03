from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class MetricType(str, Enum):
    CREDIBILITY = "credibility"
    TOPIC_AUTHORITY = "topic_authority"
    COMMUNICATION = "communication"
    FRESHNESS = "freshness"
    GROWTH = "growth"


class MetricConfig(BaseModel):
    enabled: bool = True
    weight: float = Field(ge=0, le=1, default=0.2)


class FilterConfig(BaseModel):
    subscriber_min: Optional[int] = None
    subscriber_max: Optional[int] = None
    avg_video_length_min: Optional[int] = None  # seconds
    growth_rate_min: Optional[float] = None  # percentage
    uploads_last_90_days_min: Optional[int] = None
    topic_relevance_min: Optional[float] = None  # 0-1


class SearchRequest(BaseModel):
    # Topic / expertise description
    topic_query: str = Field(..., min_length=3, max_length=500)
    topic_keywords: List[str] = []
    
    # Metric configuration
    metrics: Dict[MetricType, MetricConfig] = {
        MetricType.CREDIBILITY: MetricConfig(enabled=True, weight=0.2),
        MetricType.TOPIC_AUTHORITY: MetricConfig(enabled=True, weight=0.3),
        MetricType.COMMUNICATION: MetricConfig(enabled=True, weight=0.2),
        MetricType.FRESHNESS: MetricConfig(enabled=True, weight=0.15),
        MetricType.GROWTH: MetricConfig(enabled=True, weight=0.15),
    }
    
    # Filters
    filters: FilterConfig = FilterConfig()
    
    # Pagination
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SearchResponse(BaseModel):
    query: str
    total_results: int
    filtered_count: int
    creators: List[dict]  # List of CreatorCard
    
    # Metadata
    metrics_used: List[str]
    filters_applied: Dict[str, str]
    processing_time_ms: float


class DiscoverRequest(BaseModel):
    """For discovering new creators to add to the database"""
    search_query: str
    max_results: int = Field(default=50, ge=1, le=200)
    relevance_language: str = "en"


class ScoreExplanation(BaseModel):
    metric: str
    score: float
    available: bool
    factors: List[str]
    weight_applied: float


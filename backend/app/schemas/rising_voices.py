from datetime import date, datetime
from typing import List

from pydantic import BaseModel


class RisingVoiceScoreBreakdown(BaseModel):
    credibility: float
    topicAuthority: float
    communication: float
    freshness: float
    growth: float


class RisingVoiceResponse(BaseModel):
    name: str
    slug: str
    host: str
    subscriberCount: int
    growthSignal: str
    scoreBreakdown: RisingVoiceScoreBreakdown
    overallScore: float
    tags: List[str]
    channelUrl: str
    lastScored: date


class RisingVoicesRefreshResponse(BaseModel):
    status: str
    refreshedAt: datetime
    count: int
    endpoint: str
    apiKeyRequired: bool

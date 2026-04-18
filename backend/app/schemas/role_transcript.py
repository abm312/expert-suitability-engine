from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleTranscriptBuildRequest(BaseModel):
    roleQuery: str = Field(..., min_length=3, max_length=255)
    topChannels: int = Field(default=3, ge=1, le=5)
    videosPerChannel: int = Field(default=3, ge=1, le=5)
    minDurationMinutes: int = Field(default=20, ge=1, le=180)


class RoleTranscriptVideoResponse(BaseModel):
    videoId: str
    title: str
    videoUrl: str
    publishedAt: Optional[str] = None
    durationSeconds: int = 0
    transcriptStatus: str
    transcriptLanguage: Optional[str] = None
    transcriptError: Optional[str] = None
    segmentCount: int = 0
    transcriptText: Optional[str] = None
    fetchedFromCache: bool = False


class RoleTranscriptChannelResponse(BaseModel):
    rank: int
    channelId: str
    channelName: str
    channelUrl: str
    overallScore: float
    topicMatchSummary: str
    transcriptsFound: int
    selectedVideoCount: int
    videos: List[RoleTranscriptVideoResponse]


class RoleTranscriptDumpResponse(BaseModel):
    roleQuery: str
    roleSlug: str
    searchQueryUsed: str
    channelCount: int
    transcriptCount: int
    topChannels: int
    videosPerChannel: int
    minDurationMinutes: int
    createdAt: datetime
    refreshedAt: datetime
    expertChannels: List[RoleTranscriptChannelResponse]

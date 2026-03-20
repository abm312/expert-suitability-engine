from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class TranscriptDumpRequest(BaseModel):
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    channel_handle: Optional[str] = None
    search_query: Optional[str] = None

    max_videos: int = Field(default=3, ge=1, le=50)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    refresh: bool = False
    persist_dump_file: bool = False

    @model_validator(mode="after")
    def validate_channel_source(self) -> "TranscriptDumpRequest":
        if not any(
            [
                self.channel_id,
                self.channel_url,
                self.channel_handle,
                self.search_query,
            ]
        ):
            raise ValueError(
                "One of channel_id, channel_url, channel_handle, or search_query is required"
            )
        return self


class TranscriptSegment(BaseModel):
    text: str
    start: float = 0.0
    duration: float = 0.0


class TranscriptVideoItem(BaseModel):
    video_id: str
    title: str
    published_at: Optional[datetime] = None
    caption_hint: bool = False
    transcript_status: str
    transcript_error: Optional[str] = None
    transcript_language: Optional[str] = None
    is_generated: Optional[bool] = None
    segment_count: int = 0
    transcript_text: Optional[str] = None
    segments: list[TranscriptSegment] = Field(default_factory=list)
    fetched_from_cache: bool = False


class TranscriptDumpResponse(BaseModel):
    channel_id: str
    channel_name: str
    requested_at: datetime
    max_videos: int
    languages: list[str]
    transcripts_found: int
    dump_file: Optional[str] = None
    videos: list[TranscriptVideoItem]


class CachedTranscriptResponse(BaseModel):
    channel_id: str
    channel_name: str
    videos: list[TranscriptVideoItem]


class FillerWordStat(BaseModel):
    term: str
    count: int


class CommunicationVideoAnalysis(BaseModel):
    video_id: str
    title: str
    transcript_status: str
    word_count: int = 0
    sentence_count: int = 0
    average_sentence_length: float = 0.0
    filler_word_count: int = 0
    filler_word_ratio: float = 0.0
    top_filler_words: list[FillerWordStat] = Field(default_factory=list)


class CommunicationAnalysisResponse(BaseModel):
    channel_id: str
    channel_name: str
    analyzed_at: datetime
    total_videos_considered: int
    transcripts_analyzed: int
    total_word_count: int
    total_sentence_count: int
    average_sentence_length: float
    filler_word_count: int
    filler_word_ratio: float
    top_filler_words: list[FillerWordStat] = Field(default_factory=list)
    summary: str
    videos: list[CommunicationVideoAnalysis]

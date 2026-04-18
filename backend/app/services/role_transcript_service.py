from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any, Dict, List

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import RoleTranscriptDump
from app.schemas.role_transcript import (
    RoleTranscriptBuildRequest,
    RoleTranscriptChannelResponse,
    RoleTranscriptDumpResponse,
    RoleTranscriptVideoResponse,
)
from app.schemas.search import FilterConfig, MetricConfig, MetricType, SearchRequest
from app.services.creator_service import CreatorService
from app.services.youtube_service import YouTubeService


logger = logging.getLogger(__name__)
settings = get_settings()


ROLE_TRANSCRIPT_METRICS = {
    MetricType.CREDIBILITY: MetricConfig(enabled=True, weight=0.25),
    MetricType.TOPIC_AUTHORITY: MetricConfig(enabled=True, weight=0.40),
    MetricType.COMMUNICATION: MetricConfig(enabled=False, weight=0.0),
    MetricType.FRESHNESS: MetricConfig(enabled=True, weight=0.20),
    MetricType.GROWTH: MetricConfig(enabled=True, weight=0.15),
}

ROLE_TRANSCRIPT_FILTERS = FilterConfig(
    uploads_last_90_days_min=1,
)


class RoleTranscriptService:
    def __init__(self) -> None:
        self.creator_service = CreatorService()
        self.youtube = YouTubeService()

    async def build_dump(
        self,
        db: AsyncSession,
        request: RoleTranscriptBuildRequest,
    ) -> RoleTranscriptDumpResponse:
        role_query = request.roleQuery.strip()
        role_slug = self._slugify(role_query)
        search_query_used = self._build_search_query(role_query)

        logger.info(
            "🧾 Building role transcript dump role_query='%s' role_slug='%s' search_query='%s'",
            role_query,
            role_slug,
            search_query_used,
        )

        candidate_channels = await self._select_expert_channels(
            db,
            search_query_used,
            candidate_count=max(request.topChannels * 5, request.topChannels),
        )

        channel_entries: List[RoleTranscriptChannelResponse] = []
        total_transcripts = 0

        for creator in candidate_channels:
            channel_entry = await self._build_channel_entry(
                creator=creator,
                rank=len(channel_entries) + 1,
                videos_per_channel=request.videosPerChannel,
                min_duration_minutes=request.minDurationMinutes,
            )
            if channel_entry.selectedVideoCount == 0:
                continue
            total_transcripts += channel_entry.transcriptsFound
            channel_entries.append(channel_entry)
            if len(channel_entries) >= request.topChannels:
                break

        if not channel_entries:
            raise ValueError(
                f"No long-form transcript candidates found for '{role_query}'"
            )

        existing = await self._get_dump_row(db, role_slug)
        created_at = existing.created_at if existing else datetime.utcnow()
        refreshed_at = datetime.utcnow()

        response = RoleTranscriptDumpResponse(
            roleQuery=role_query,
            roleSlug=role_slug,
            searchQueryUsed=search_query_used,
            channelCount=len(channel_entries),
            transcriptCount=total_transcripts,
            topChannels=request.topChannels,
            videosPerChannel=request.videosPerChannel,
            minDurationMinutes=request.minDurationMinutes,
            createdAt=created_at,
            refreshedAt=refreshed_at,
            expertChannels=channel_entries,
        )

        payload = response.model_dump(mode="json")
        if existing:
            existing.role_query = role_query
            existing.search_query_used = search_query_used
            existing.channel_count = response.channelCount
            existing.transcript_count = response.transcriptCount
            existing.dump_json = payload
            existing.refreshed_at = refreshed_at
        else:
            db.add(
                RoleTranscriptDump(
                    role_slug=role_slug,
                    role_query=role_query,
                    search_query_used=search_query_used,
                    channel_count=response.channelCount,
                    transcript_count=response.transcriptCount,
                    dump_json=payload,
                    created_at=created_at,
                    refreshed_at=refreshed_at,
                )
            )

        await db.flush()
        logger.info(
            "✅ Role transcript dump stored role_slug='%s' channels=%s transcripts=%s",
            role_slug,
            response.channelCount,
            response.transcriptCount,
        )
        return response

    async def get_dump(self, db: AsyncSession, role_slug: str) -> RoleTranscriptDumpResponse | None:
        row = await self._get_dump_row(db, role_slug)
        if not row:
            return None
        return RoleTranscriptDumpResponse.model_validate(row.dump_json)

    async def download_dump_payload(self, db: AsyncSession, role_slug: str) -> Dict[str, Any] | None:
        row = await self._get_dump_row(db, role_slug)
        if not row:
            return None
        return row.dump_json

    async def _get_dump_row(
        self,
        db: AsyncSession,
        role_slug: str,
    ) -> RoleTranscriptDump | None:
        result = await db.execute(
            select(RoleTranscriptDump).where(RoleTranscriptDump.role_slug == role_slug)
        )
        return result.scalar_one_or_none()

    async def _select_expert_channels(
        self,
        db: AsyncSession,
        search_query: str,
        candidate_count: int,
    ) -> List[Dict[str, Any]]:
        request = SearchRequest(
            topic_query=search_query,
            topic_keywords=[],
            metrics=ROLE_TRANSCRIPT_METRICS,
            filters=ROLE_TRANSCRIPT_FILTERS,
            limit=candidate_count,
            offset=0,
        )
        results = await self.creator_service.search_creators(db, request)
        creators = results.get("creators", [])
        if not creators:
            raise ValueError(f"No expert channels found for '{search_query}'")
        return creators[:candidate_count]

    async def _build_channel_entry(
        self,
        creator: Dict[str, Any],
        rank: int,
        videos_per_channel: int,
        min_duration_minutes: int,
    ) -> RoleTranscriptChannelResponse:
        channel_id = creator["channel_id"]
        recent_video_scan_limit = max(videos_per_channel * 3, videos_per_channel)

        youtube_videos = await self.youtube.get_channel_videos(
            channel_id,
            max_results=recent_video_scan_limit,
        )
        sorted_videos = sorted(
            youtube_videos,
            key=lambda video: video.get("published_at") or "",
            reverse=True,
        )
        selected_videos = self._select_recent_episode_candidates(
            sorted_videos,
            videos_per_channel,
            min_duration_minutes=min_duration_minutes,
        )
        selected_video_ids = {video["video_id"] for video in selected_videos}
        if not selected_video_ids:
            return RoleTranscriptChannelResponse(
                rank=rank,
                channelId=channel_id,
                channelName=creator["channel_name"],
                channelUrl=creator.get("channel_url") or f"https://youtube.com/channel/{channel_id}",
                overallScore=float(creator.get("overall_score") or 0.0),
                topicMatchSummary=creator.get("topic_match_summary") or "",
                transcriptsFound=0,
                selectedVideoCount=0,
                videos=[],
            )

        transcript_dump = await self._fetch_selected_video_transcripts(
            channel_id=channel_id,
            video_ids=[video["video_id"] for video in selected_videos],
        )
        transcript_items = {
            item["video_id"]: item
            for item in transcript_dump.get("videos", [])
        }

        videos: List[RoleTranscriptVideoResponse] = []
        transcripts_found = 0
        for video in selected_videos:
            transcript_item = transcript_items.get(video["video_id"], {})
            status = transcript_item.get("transcript_status", "missing")
            if status == "fetched":
                transcripts_found += 1

            videos.append(
                RoleTranscriptVideoResponse(
                    videoId=video["video_id"],
                    title=video.get("title") or video["video_id"],
                    videoUrl=f"https://www.youtube.com/watch?v={video['video_id']}",
                    publishedAt=video.get("published_at"),
                    durationSeconds=int(video.get("duration_seconds") or 0),
                    transcriptStatus=status,
                    transcriptLanguage=transcript_item.get("transcript_language"),
                    transcriptError=transcript_item.get("transcript_error"),
                    segmentCount=int(transcript_item.get("segment_count") or 0),
                    transcriptText=transcript_item.get("transcript_text"),
                    fetchedFromCache=bool(transcript_item.get("fetched_from_cache")),
                )
            )

        return RoleTranscriptChannelResponse(
            rank=rank,
            channelId=channel_id,
            channelName=creator["channel_name"],
            channelUrl=creator.get("channel_url") or f"https://youtube.com/channel/{channel_id}",
            overallScore=float(creator.get("overall_score") or 0.0),
            topicMatchSummary=creator.get("topic_match_summary") or "",
            transcriptsFound=transcripts_found,
            selectedVideoCount=len(videos),
            videos=videos,
        )

    async def _fetch_selected_video_transcripts(
        self,
        channel_id: str,
        video_ids: List[str],
    ) -> Dict[str, Any]:
        base_url = (settings.TRANSCRIPT_SERVICE_URL or "").rstrip("/")
        if not base_url:
            raise RuntimeError("TRANSCRIPT_SERVICE_URL is not configured")

        payload = {
            "channel_id": channel_id,
            "video_ids": video_ids,
            "languages": ["en"],
            "refresh": True,
            "persist_dump_file": False,
        }
        url = f"{base_url}/transcripts/videos"
        logger.info(
            "📼 Fetching selected-video transcripts channel_id=%s video_count=%s url=%s",
            channel_id,
            len(video_ids),
            url,
        )

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(url, json=payload)

        if response.status_code >= 400:
            detail = response.text[:500]
            raise RuntimeError(
                f"Transcript service request failed for {channel_id}: HTTP {response.status_code} {detail}"
            )

        return response.json()

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "role"

    @staticmethod
    def _build_search_query(role_query: str) -> str:
        lowered = role_query.lower()
        ai_markers = ("ai", "llm", "gpt", "genai", "agent", "artificial intelligence")
        if any(marker in lowered for marker in ai_markers):
            return role_query
        return f"AI for {role_query}"

    @staticmethod
    def _select_recent_episode_candidates(
        videos: List[Dict[str, Any]],
        videos_per_channel: int,
        min_duration_minutes: int,
    ) -> List[Dict[str, Any]]:
        min_duration_seconds = max(60, min_duration_minutes * 60)
        long_form = [
            video for video in videos
            if int(video.get("duration_seconds") or 0) >= min_duration_seconds
        ]
        return long_form[:videos_per_channel]

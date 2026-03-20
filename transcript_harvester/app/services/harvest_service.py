from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from app.core.config import Settings
from app.schemas import TranscriptDumpRequest, TranscriptDumpResponse, TranscriptVideoItem
from app.services.transcript_fetcher import TranscriptFetcher
from app.services.youtube_catalog import YouTubeCatalogService
from app.store import SQLiteStore


logger = logging.getLogger(__name__)


class HarvestService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = SQLiteStore(settings.database_path)
        self.youtube = YouTubeCatalogService(settings.YOUTUBE_API_KEY)
        self.transcripts = TranscriptFetcher(settings)

        Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        logger.info(
            "HarvestService initialized provider=%s missing_transcript_cache_seconds=%s database_path=%s",
            self.transcripts.provider,
            self.settings.MISSING_TRANSCRIPT_CACHE_SECONDS,
            self.settings.database_path,
        )

    def fetch_transcript_dump(self, request: TranscriptDumpRequest) -> TranscriptDumpResponse:
        logger.info(
            "Starting transcript dump source(channel_id=%s, channel_url=%s, channel_handle=%s, search_query=%s) max_videos=%s languages=%s refresh=%s provider=%s",
            request.channel_id,
            request.channel_url,
            request.channel_handle,
            request.search_query,
            request.max_videos,
            request.languages,
            request.refresh,
            self.transcripts.provider,
        )
        channel = self.youtube.resolve_channel(
            channel_id=request.channel_id,
            channel_url=request.channel_url,
            channel_handle=request.channel_handle,
            search_query=request.search_query,
        )
        logger.info(
            "Resolved channel channel_id=%s channel_name=%s",
            channel["channel_id"],
            channel["channel_name"],
        )
        videos = self.youtube.get_recent_videos(channel["channel_id"], request.max_videos)
        logger.info(
            "Loaded recent videos channel_id=%s requested_max=%s actual_count=%s",
            channel["channel_id"],
            request.max_videos,
            len(videos),
        )

        self.store.upsert_channel(channel)
        self.store.upsert_videos(channel["channel_id"], videos)

        items: list[TranscriptVideoItem] = []
        for video in videos:
            cached = (
                None
                if request.refresh
                else self.store.get_cached_transcript(
                    video["video_id"],
                    missing_ttl_seconds=self.settings.MISSING_TRANSCRIPT_CACHE_SECONDS,
                )
            )
            if cached:
                logger.info(
                    "Transcript cache hit video_id=%s title=%s cached_status=%s has_text=%s",
                    video["video_id"],
                    video["title"],
                    cached.get("transcript_status"),
                    bool(cached.get("transcript_text")),
                )
                items.append(
                    TranscriptVideoItem(
                        **cached,
                        fetched_from_cache=True,
                    )
                )
                continue

            attempted_at = datetime.utcnow().isoformat()
            try:
                logger.info(
                    "Transcript fetch miss video_id=%s title=%s provider=%s languages=%s",
                    video["video_id"],
                    video["title"],
                    self.transcripts.provider,
                    request.languages,
                )
                transcript = self.transcripts.fetch(video["video_id"], request.languages)
                self.store.save_transcript(video["video_id"], transcript, attempted_at)
                logger.info(
                    "Transcript fetch success video_id=%s language=%s segment_count=%s word_count=%s generated=%s",
                    video["video_id"],
                    transcript.get("language"),
                    transcript["segment_count"],
                    len((transcript.get("text") or "").split()),
                    transcript.get("is_generated"),
                )
                items.append(
                    TranscriptVideoItem(
                        video_id=video["video_id"],
                        title=video["title"],
                        published_at=self._parse_datetime(video.get("published_at")),
                        caption_hint=bool(video.get("caption_hint")),
                        transcript_status="fetched",
                        transcript_language=transcript.get("language"),
                        is_generated=transcript.get("is_generated"),
                        segment_count=transcript["segment_count"],
                        transcript_text=transcript["text"],
                        segments=transcript["segments"],
                        fetched_from_cache=False,
                    )
                )
            except Exception as exc:
                error = self._clean_error(str(exc))
                self.store.mark_transcript_failure(video["video_id"], error, attempted_at)
                logger.warning(
                    "Transcript fetch failed video_id=%s title=%s provider=%s error=%s",
                    video["video_id"],
                    video["title"],
                    self.transcripts.provider,
                    error,
                )
                items.append(
                    TranscriptVideoItem(
                        video_id=video["video_id"],
                        title=video["title"],
                        published_at=self._parse_datetime(video.get("published_at")),
                        caption_hint=bool(video.get("caption_hint")),
                        transcript_status="missing",
                        transcript_error=error,
                        segment_count=0,
                        transcript_text=None,
                        segments=[],
                        fetched_from_cache=False,
                    )
                )

        response = TranscriptDumpResponse(
            channel_id=channel["channel_id"],
            channel_name=channel["channel_name"],
            requested_at=datetime.utcnow(),
            max_videos=request.max_videos,
            languages=request.languages,
            transcripts_found=sum(1 for item in items if item.transcript_status == "fetched"),
            videos=items,
        )

        if request.persist_dump_file:
            dump_path = self.persist_dump(response)
            response.dump_file = str(dump_path)
            logger.info(
                "Transcript dump persisted channel_id=%s path=%s",
                response.channel_id,
                response.dump_file,
            )

        logger.info(
            "Transcript dump finished channel_id=%s channel_name=%s transcripts_found=%s total_videos=%s",
            response.channel_id,
            response.channel_name,
            response.transcripts_found,
            len(response.videos),
        )

        return response

    def get_cached_transcripts(self, channel_id: str, max_videos: int) -> TranscriptDumpResponse:
        logger.info(
            "Loading cached transcripts channel_id=%s max_videos=%s",
            channel_id,
            max_videos,
        )
        channel_name = self.store.get_channel_name(channel_id)
        if not channel_name:
            raise ValueError(f"Channel '{channel_id}' is not cached yet")

        items = [
            TranscriptVideoItem(**item, fetched_from_cache=bool(item.get("transcript_text")))
            for item in self.store.get_cached_channel_transcripts(channel_id, max_videos)
        ]

        response = TranscriptDumpResponse(
            channel_id=channel_id,
            channel_name=channel_name,
            requested_at=datetime.utcnow(),
            max_videos=max_videos,
            languages=self.settings.DEFAULT_LANGUAGES,
            transcripts_found=sum(1 for item in items if item.transcript_status == "fetched"),
            videos=items,
        )
        logger.info(
            "Loaded cached transcripts channel_id=%s channel_name=%s transcripts_found=%s total_videos=%s",
            response.channel_id,
            response.channel_name,
            response.transcripts_found,
            len(response.videos),
        )
        return response

    def persist_dump(self, response: TranscriptDumpResponse) -> Path:
        slug = self._slugify(response.channel_name)
        timestamp = response.requested_at.strftime("%Y%m%dT%H%M%S")
        path = Path(self.settings.OUTPUT_DIR) / f"{slug}-{timestamp}.json"
        path.write_text(
            json.dumps(response.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
        return slug or "channel"

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    @staticmethod
    def _clean_error(error: str) -> str:
        trimmed = error.strip()
        return trimmed[:300] if len(trimmed) > 300 else trimmed

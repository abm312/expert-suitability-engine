from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from app.core.config import Settings
from app.schemas import TranscriptDumpRequest, TranscriptDumpResponse, TranscriptVideoItem
from app.services.transcript_fetcher import TranscriptFetcher
from app.services.youtube_catalog import YouTubeCatalogService
from app.store import SQLiteStore


class HarvestService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = SQLiteStore(settings.database_path)
        self.youtube = YouTubeCatalogService(settings.YOUTUBE_API_KEY)
        self.transcripts = TranscriptFetcher()

        Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    def fetch_transcript_dump(self, request: TranscriptDumpRequest) -> TranscriptDumpResponse:
        channel = self.youtube.resolve_channel(
            channel_id=request.channel_id,
            channel_url=request.channel_url,
            channel_handle=request.channel_handle,
            search_query=request.search_query,
        )
        videos = self.youtube.get_recent_videos(channel["channel_id"], request.max_videos)

        self.store.upsert_channel(channel)
        self.store.upsert_videos(channel["channel_id"], videos)

        items: list[TranscriptVideoItem] = []
        for video in videos:
            cached = None if request.refresh else self.store.get_cached_transcript(video["video_id"])
            if cached:
                items.append(
                    TranscriptVideoItem(
                        **cached,
                        fetched_from_cache=True,
                    )
                )
                continue

            attempted_at = datetime.utcnow().isoformat()
            try:
                transcript = self.transcripts.fetch(video["video_id"], request.languages)
                self.store.save_transcript(video["video_id"], transcript, attempted_at)
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

        return response

    def get_cached_transcripts(self, channel_id: str, max_videos: int) -> TranscriptDumpResponse:
        channel_name = self.store.get_channel_name(channel_id)
        if not channel_name:
            raise ValueError(f"Channel '{channel_id}' is not cached yet")

        items = [
            TranscriptVideoItem(**item, fetched_from_cache=bool(item.get("transcript_text")))
            for item in self.store.get_cached_channel_transcripts(channel_id, max_videos)
        ]

        return TranscriptDumpResponse(
            channel_id=channel_id,
            channel_name=channel_name,
            requested_at=datetime.utcnow(),
            max_videos=max_videos,
            languages=self.settings.DEFAULT_LANGUAGES,
            transcripts_found=sum(1 for item in items if item.transcript_status == "fetched"),
            videos=items,
        )

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

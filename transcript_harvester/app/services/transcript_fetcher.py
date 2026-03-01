from __future__ import annotations

from datetime import datetime
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi


class TranscriptFetcher:
    def __init__(self) -> None:
        try:
            self.api = YouTubeTranscriptApi()
        except TypeError:
            self.api = None

    def fetch(self, video_id: str, languages: list[str]) -> dict[str, Any]:
        payload = self._fetch_raw(video_id, languages)
        normalized = self._normalize_payload(payload)

        if not normalized["segments"]:
            raise RuntimeError("Transcript fetch returned no segments")

        text = " ".join(segment["text"] for segment in normalized["segments"]).strip()
        normalized["text"] = text
        normalized["segment_count"] = len(normalized["segments"])
        normalized["fetched_at"] = datetime.utcnow().isoformat()
        return normalized

    def _fetch_raw(self, video_id: str, languages: list[str]) -> Any:
        if self.api and hasattr(self.api, "fetch"):
            return self.api.fetch(video_id, languages=languages)

        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            return YouTubeTranscriptApi.get_transcript(video_id, languages=languages)

        raise RuntimeError("Unsupported youtube-transcript-api version")

    def _normalize_payload(self, payload: Any) -> dict[str, Any]:
        language = getattr(payload, "language", None)
        is_generated = getattr(payload, "is_generated", None)

        if hasattr(payload, "snippets"):
            snippets = payload.snippets
        elif isinstance(payload, list):
            snippets = payload
        else:
            try:
                snippets = list(payload)
            except TypeError as exc:
                raise RuntimeError("Unable to normalize transcript payload") from exc

        segments = []
        for item in snippets:
            text = self._read_attr(item, "text", "")
            if not text:
                continue
            segments.append(
                {
                    "text": text,
                    "start": float(self._read_attr(item, "start", 0.0)),
                    "duration": float(self._read_attr(item, "duration", 0.0)),
                }
            )

        return {
            "language": language,
            "is_generated": is_generated,
            "segments": segments,
        }

    @staticmethod
    def _read_attr(item: Any, key: str, default: Any) -> Any:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

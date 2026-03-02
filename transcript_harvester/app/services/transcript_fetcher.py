from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from youtube_transcript_api import YouTubeTranscriptApi

from app.core.config import Settings


class TranscriptFetcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = self._resolve_provider()
        self.session = requests.Session()
        try:
            self.api = YouTubeTranscriptApi()
        except TypeError:
            self.api = None

    def fetch(self, video_id: str, languages: list[str]) -> dict[str, Any]:
        if self.provider == "rapidapi":
            normalized = self._fetch_via_rapidapi(video_id, languages)
        else:
            payload = self._fetch_raw(video_id, languages)
            normalized = self._normalize_payload(payload)

        if not normalized["segments"]:
            raise RuntimeError("Transcript fetch returned no segments")

        text = " ".join(segment["text"] for segment in normalized["segments"]).strip()
        normalized["text"] = text
        normalized["segment_count"] = len(normalized["segments"])
        normalized["fetched_at"] = datetime.utcnow().isoformat()
        return normalized

    def _resolve_provider(self) -> str:
        configured = (self.settings.TRANSCRIPT_PROVIDER or "auto").strip().lower()
        if configured in {"rapidapi", "youtube_transcript_api"}:
            return configured
        if self.settings.RAPIDAPI_KEY:
            return "rapidapi"
        return "youtube_transcript_api"

    def _fetch_via_rapidapi(self, video_id: str, languages: list[str]) -> dict[str, Any]:
        if not self.settings.RAPIDAPI_KEY:
            raise RuntimeError("RAPIDAPI_KEY is not configured")

        params: dict[str, str] = {"videoId": video_id}
        preferred_language = self._pick_rapidapi_language(languages)
        if preferred_language:
            params["lang"] = preferred_language

        try:
            response = self.session.get(
                f"{self.settings.rapidapi_base_url}/api/transcript",
                params=params,
                headers={
                    "x-rapidapi-host": self.settings.RAPIDAPI_HOST,
                    "x-rapidapi-key": self.settings.RAPIDAPI_KEY,
                },
                timeout=self.settings.RAPIDAPI_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"RapidAPI request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("RapidAPI returned non-JSON transcript data") from exc

        if not payload.get("success"):
            error = (payload.get("error") or "Unknown RapidAPI transcript error").strip()
            raise RuntimeError(f"RapidAPI transcript fetch failed: {error}")

        transcript = payload.get("transcript")
        if isinstance(transcript, str):
            text = transcript.strip()
            if not text:
                raise RuntimeError("RapidAPI transcript fetch returned empty text")
            return {
                "language": preferred_language,
                "is_generated": None,
                "segments": [
                    {
                        "text": text,
                        "start": 0.0,
                        "duration": 0.0,
                    }
                ],
            }

        if not isinstance(transcript, list):
            raise RuntimeError("RapidAPI transcript response is not in the expected format")

        segments = []
        transcript_language = preferred_language
        for item in transcript:
            text = self._read_attr(item, "text", "").strip()
            if not text:
                continue
            transcript_language = self._read_attr(item, "lang", transcript_language)
            segments.append(
                {
                    "text": text,
                    "start": float(self._read_attr(item, "offset", 0.0)),
                    "duration": float(self._read_attr(item, "duration", 0.0)),
                }
            )

        return {
            "language": transcript_language,
            "is_generated": None,
            "segments": segments,
        }

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

    @staticmethod
    def _pick_rapidapi_language(languages: list[str]) -> str | None:
        if not languages:
            return None
        preferred = (languages[0] or "").strip()
        return preferred or None

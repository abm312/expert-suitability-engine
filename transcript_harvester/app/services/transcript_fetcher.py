from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import requests
from youtube_transcript_api import YouTubeTranscriptApi

from app.core.config import Settings

logger = logging.getLogger(__name__)


class TranscriptFetcher:
    TRANSIENT_HTTP_STATUS_CODES = {408, 429, 500, 502, 503, 504}
    RETRYABLE_PROVIDER_ERROR_MARKERS = (
        "not available at the moment for this video or language",
        "not available for this video or language",
    )

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

        preferred_language = self._pick_rapidapi_language(languages)
        language_label = preferred_language or "auto"
        logger.info(
            "RapidAPI transcript fetch start video_id=%s language=%s",
            video_id,
            language_label,
        )

        payload = self._request_rapidapi(video_id, preferred_language)
        normalized = self._normalize_rapidapi_payload(payload.get("transcript"), preferred_language)
        if not normalized["segments"]:
            raise RuntimeError(
                f"RapidAPI transcript fetch failed (lang={language_label}): Transcript fetch returned no segments"
            )
        return normalized

    def _request_rapidapi(self, video_id: str, language: str | None) -> dict[str, Any]:
        params: dict[str, str] = {"videoId": video_id}
        if language:
            params["lang"] = language

        language_label = language or "auto"
        max_attempts = max(1, int(self.settings.RAPIDAPI_MAX_ATTEMPTS))
        for attempt in range(1, max_attempts + 1):
            response: requests.Response | None = None
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
            except requests.Timeout as exc:
                if self._can_retry_attempt(attempt, max_attempts):
                    self._sleep_before_retry(attempt)
                    continue
                raise RuntimeError(
                    f"RapidAPI request failed (lang={language_label}) after {attempt} attempts: timeout: {exc}"
                ) from exc
            except requests.RequestException as exc:
                if self._can_retry_attempt(attempt, max_attempts):
                    self._sleep_before_retry(attempt)
                    continue
                raise RuntimeError(
                    f"RapidAPI request failed (lang={language_label}) after {attempt} attempts: {exc}"
                ) from exc

            if response.status_code in self.TRANSIENT_HTTP_STATUS_CODES:
                if self._can_retry_attempt(attempt, max_attempts):
                    self._sleep_before_retry(attempt)
                    continue
                excerpt = response.text.strip()[:240]
                raise RuntimeError(
                    f"RapidAPI request failed (lang={language_label}) after {attempt} attempts: HTTP {response.status_code} {excerpt}"
                )

            if response.status_code >= 400:
                excerpt = response.text.strip()[:240]
                raise RuntimeError(
                    f"RapidAPI request failed (lang={language_label}): HTTP {response.status_code} {excerpt}"
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise RuntimeError("RapidAPI returned non-JSON transcript data") from exc

            if payload.get("success"):
                return payload

            provider_error = (payload.get("error") or "Unknown RapidAPI transcript error").strip()
            if (
                self._can_retry_attempt(attempt, max_attempts)
                and self._is_retryable_provider_error(provider_error)
            ):
                logger.warning(
                    "RapidAPI provider returned retryable transcript miss for video_id=%s lang=%s attempt=%s/%s; retrying. error=%s",
                    video_id,
                    language_label,
                    attempt,
                    max_attempts,
                    provider_error,
                )
                self._sleep_before_retry(attempt)
                continue

            raise RuntimeError(
                f"RapidAPI transcript fetch failed (lang={language_label}) after {attempt} attempts: {provider_error}"
            )

        raise RuntimeError(
            f"RapidAPI request failed (lang={language_label}) after {max_attempts} attempts: unknown reason"
        )

    def _normalize_rapidapi_payload(
        self, transcript: Any, requested_language: str | None
    ) -> dict[str, Any]:
        if isinstance(transcript, str):
            text = transcript.strip()
            if not text:
                return {
                    "language": requested_language,
                    "is_generated": None,
                    "segments": [],
                }
            return {
                "language": requested_language,
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
        transcript_language = requested_language
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
        for language in languages:
            normalized = (language or "").strip()
            if normalized:
                return normalized
        return None

    def _can_retry_attempt(self, attempt: int, max_attempts: int) -> bool:
        return attempt < max_attempts

    def _sleep_before_retry(self, attempt: int) -> None:
        base = max(0.0, float(self.settings.RAPIDAPI_RETRY_BASE_SECONDS))
        cap = max(base, float(self.settings.RAPIDAPI_RETRY_MAX_SECONDS))
        delay = min(cap, base * (2 ** max(0, attempt - 1)))
        if delay > 0:
            time.sleep(delay)

    def _is_retryable_provider_error(self, error: str) -> bool:
        normalized = error.lower()
        return any(marker in normalized for marker in self.RETRYABLE_PROVIDER_ERROR_MARKERS)

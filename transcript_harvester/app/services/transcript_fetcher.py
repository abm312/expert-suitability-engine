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
    TRANSCRIPT_UNAVAILABLE_ERROR_MARKERS = (
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
        if self.provider == "supadata":
            normalized = self._fetch_via_supadata(video_id, languages)
        elif self.provider == "rapidapi":
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
        if configured in {"supadata", "rapidapi", "youtube_transcript_api"}:
            return configured
        if self.settings.SUPADATA_API_KEY:
            return "supadata"
        if self.settings.RAPIDAPI_KEY:
            return "rapidapi"
        return "youtube_transcript_api"

    def _fetch_via_supadata(self, video_id: str, languages: list[str]) -> dict[str, Any]:
        if not self.settings.SUPADATA_API_KEY:
            raise RuntimeError("SUPADATA_API_KEY is not configured")

        requested_language = self._pick_requested_language(languages)
        params: dict[str, Any] = {
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "text": "false",
            "mode": (self.settings.SUPADATA_MODE or "auto").strip().lower() or "auto",
        }
        if requested_language:
            params["lang"] = requested_language

        response = self._supadata_get("/transcript", params)
        if response.status_code == 202:
            payload = response.json()
            job_id = payload.get("jobId")
            if not job_id:
                raise RuntimeError("Supadata returned 202 without a jobId")
            payload = self._poll_supadata_job(job_id)
        else:
            payload = self._parse_json_response(response, "Supadata returned non-JSON transcript data")

        transcript = payload.get("content") or payload.get("transcript") or payload.get("result")
        return self._normalize_supadata_payload(transcript, requested_language)

    def _fetch_via_rapidapi(self, video_id: str, languages: list[str]) -> dict[str, Any]:
        if not self.settings.RAPIDAPI_KEY:
            raise RuntimeError("RAPIDAPI_KEY is not configured")

        language_candidates = self._build_rapidapi_language_candidates(languages)
        errors: list[str] = []

        for language in language_candidates:
            language_label = language or "auto"
            logger.info(
                "RapidAPI transcript fetch start video_id=%s language=%s",
                video_id,
                language_label,
            )

            try:
                payload = self._request_rapidapi(video_id, language)
                normalized = self._normalize_rapidapi_payload(payload.get("transcript"), language)
                if not normalized["segments"]:
                    raise RuntimeError(
                        f"RapidAPI transcript fetch failed (lang={language_label}): Transcript fetch returned no segments"
                    )
                return normalized
            except Exception as exc:
                message = str(exc).strip()
                errors.append(f"{language_label}: {message}")

                # If a language-specific miss happens, try one final "auto" call before failing.
                if (
                    language is not None
                    and self.settings.RAPIDAPI_FALLBACK_TO_AUTO_LANGUAGE
                    and self._is_transcript_unavailable_error(message)
                ):
                    logger.warning(
                        "RapidAPI transcript miss for video_id=%s lang=%s; retrying once with auto language.",
                        video_id,
                        language_label,
                    )
                    continue

                # For other errors, stop immediately unless another language candidate exists.
                if language == language_candidates[-1]:
                    break

        raise RuntimeError(
            f"RapidAPI transcript fetch failed for video_id={video_id}: {' | '.join(errors)}"
        )

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

            provider_error = self._coerce_text(
                payload.get("error") or "Unknown RapidAPI transcript error"
            ).strip()

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
            text = self._coerce_text(self._read_attr(item, "text", "")).strip()
            if not text:
                continue
            transcript_language = self._coerce_optional_text(
                self._read_attr(item, "lang", transcript_language)
            )
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

    def _supadata_get(self, path: str, params: dict[str, Any]) -> requests.Response:
        max_attempts = max(1, int(self.settings.SUPADATA_MAX_ATTEMPTS))
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.session.get(
                    f"{self.settings.SUPADATA_BASE_URL.rstrip('/')}{path}",
                    params=params,
                    headers={
                        "x-api-key": self.settings.SUPADATA_API_KEY,
                    },
                    timeout=self.settings.SUPADATA_TIMEOUT_SECONDS,
                )
            except requests.Timeout as exc:
                if self._can_retry_attempt(attempt, max_attempts):
                    self._sleep_before_supadata_retry(attempt)
                    continue
                raise RuntimeError(f"Supadata request timed out: {exc}") from exc
            except requests.RequestException as exc:
                if self._can_retry_attempt(attempt, max_attempts):
                    self._sleep_before_supadata_retry(attempt)
                    continue
                raise RuntimeError(f"Supadata request failed: {exc}") from exc

            if response.status_code in self.TRANSIENT_HTTP_STATUS_CODES:
                if self._can_retry_attempt(attempt, max_attempts):
                    self._sleep_before_supadata_retry(attempt)
                    continue
                excerpt = response.text.strip()[:240]
                raise RuntimeError(
                    f"Supadata request failed after {attempt} attempts: HTTP {response.status_code} {excerpt}"
                )

            if response.status_code >= 400:
                excerpt = response.text.strip()[:240]
                raise RuntimeError(
                    f"Supadata request failed: HTTP {response.status_code} {excerpt}"
                )

            return response

        raise RuntimeError(
            f"Supadata request failed after {max_attempts} attempts: unknown reason"
        )

    def _poll_supadata_job(self, job_id: str) -> dict[str, Any]:
        max_attempts = max(1, int(self.settings.SUPADATA_MAX_POLL_ATTEMPTS))
        poll_interval = max(0.1, float(self.settings.SUPADATA_POLL_INTERVAL_SECONDS))

        for attempt in range(1, max_attempts + 1):
            response = self._supadata_get(f"/transcript/{job_id}", {})
            payload = self._parse_json_response(
                response,
                "Supadata returned non-JSON transcript job data",
            )

            status = self._coerce_text(payload.get("status", "")).strip().lower()
            if status in {"completed", "succeeded", "success", "done"}:
                return payload
            if status in {"failed", "error"}:
                error = self._coerce_text(payload.get("message") or payload.get("error") or "Supadata job failed")
                raise RuntimeError(error)

            if attempt < max_attempts:
                time.sleep(poll_interval)

        raise RuntimeError(
            f"Supadata transcript job did not finish after {max_attempts} polls"
        )

    def _normalize_supadata_payload(
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
            raise RuntimeError("Supadata transcript response is not in the expected format")

        segments = []
        transcript_language = requested_language
        is_generated = None

        for item in transcript:
            text = self._coerce_text(self._read_attr(item, "text", "")).strip()
            if not text:
                continue

            transcript_language = self._coerce_optional_text(
                self._read_attr(item, "lang", transcript_language)
            )
            generated_value = self._read_attr(item, "generated", is_generated)
            if isinstance(generated_value, bool):
                is_generated = generated_value

            segments.append(
                {
                    "text": text,
                    "start": float(self._read_attr(item, "offset", self._read_attr(item, "start", 0.0))),
                    "duration": float(self._read_attr(item, "duration", 0.0)),
                }
            )

        return {
            "language": transcript_language,
            "is_generated": is_generated,
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
            text = self._coerce_text(self._read_attr(item, "text", ""))
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
    def _coerce_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _coerce_optional_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    @staticmethod
    def _parse_json_response(response: requests.Response, error_message: str) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(error_message) from exc
        if not isinstance(payload, dict):
            raise RuntimeError(error_message)
        return payload

    @staticmethod
    def _pick_requested_language(languages: list[str]) -> str | None:
        for language in languages:
            normalized = (language or "").strip()
            if normalized:
                return normalized
        return None

    def _build_rapidapi_language_candidates(self, languages: list[str]) -> list[str | None]:
        candidates: list[str | None] = []
        seen: set[str | None] = set()

        for language in languages:
            normalized = (language or "").strip()
            if normalized and normalized not in seen:
                candidates.append(normalized)
                seen.add(normalized)

        if self.settings.RAPIDAPI_FALLBACK_TO_AUTO_LANGUAGE and None not in seen:
            candidates.append(None)

        if not candidates:
            candidates.append(None)

        return candidates

    def _can_retry_attempt(self, attempt: int, max_attempts: int) -> bool:
        return attempt < max_attempts

    def _sleep_before_retry(self, attempt: int) -> None:
        base = max(0.0, float(self.settings.RAPIDAPI_RETRY_BASE_SECONDS))
        cap = max(base, float(self.settings.RAPIDAPI_RETRY_MAX_SECONDS))
        delay = min(cap, base * (2 ** max(0, attempt - 1)))
        if delay > 0:
            time.sleep(delay)

    def _sleep_before_supadata_retry(self, attempt: int) -> None:
        base = max(0.0, float(self.settings.SUPADATA_RETRY_BASE_SECONDS))
        cap = max(base, float(self.settings.SUPADATA_RETRY_MAX_SECONDS))
        delay = min(cap, base * (2 ** max(0, attempt - 1)))
        if delay > 0:
            time.sleep(delay)

    def _is_transcript_unavailable_error(self, error: str) -> bool:
        normalized = error.lower()
        return any(marker in normalized for marker in self.TRANSCRIPT_UNAVAILABLE_ERROR_MARKERS)

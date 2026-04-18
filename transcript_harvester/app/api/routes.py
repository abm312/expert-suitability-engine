import json
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.core.config import get_settings
from app.schemas import TranscriptDumpRequest, TranscriptDumpResponse, TranscriptVideoDumpRequest
from app.services.communication_analyzer import CommunicationAnalyzer
from app.services.harvest_service import HarvestService


settings = get_settings()
service = HarvestService(settings)
analyzer = CommunicationAnalyzer()

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "youtube_api_configured": bool(settings.YOUTUBE_API_KEY),
        "supadata_api_configured": bool(settings.SUPADATA_API_KEY),
        "rapidapi_configured": bool(settings.RAPIDAPI_KEY),
        "transcript_provider": service.transcripts.provider,
        "supadata_mode": settings.SUPADATA_MODE,
        "missing_transcript_cache_seconds": settings.MISSING_TRANSCRIPT_CACHE_SECONDS,
        "database_path": str(settings.database_path),
    }


@router.post("/transcripts/dump")
def create_transcript_dump(request: TranscriptDumpRequest):
    logger.info(
        "Transcript dump request received channel_id=%s channel_url=%s channel_handle=%s search_query=%s max_videos=%s languages=%s refresh=%s",
        request.channel_id,
        request.channel_url,
        request.channel_handle,
        request.search_query,
        request.max_videos,
        request.languages,
        request.refresh,
    )
    try:
        dump = service.fetch_transcript_dump(request)
        logger.info(
            "Transcript dump completed channel_id=%s channel_name=%s transcripts_found=%s total_videos=%s",
            dump.channel_id,
            dump.channel_name,
            dump.transcripts_found,
            len(dump.videos),
        )
        return dump
    except Exception as exc:
        logger.exception("Transcript dump request failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/transcripts/videos")
def create_selected_video_transcript_dump(request: TranscriptVideoDumpRequest):
    logger.info(
        "Selected-video transcript dump request received channel_id=%s video_count=%s languages=%s refresh=%s",
        request.channel_id,
        len(request.video_ids),
        request.languages,
        request.refresh,
    )
    try:
        dump = service.fetch_selected_video_transcript_dump(request)
        logger.info(
            "Selected-video transcript dump completed channel_id=%s channel_name=%s transcripts_found=%s total_videos=%s",
            dump.channel_id,
            dump.channel_name,
            dump.transcripts_found,
            len(dump.videos),
        )
        return dump
    except Exception as exc:
        logger.exception("Selected-video transcript dump request failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/transcripts/download")
def download_transcript_dump(request: TranscriptDumpRequest):
    logger.info(
        "Transcript download request received channel_id=%s channel_url=%s channel_handle=%s search_query=%s max_videos=%s languages=%s refresh=%s",
        request.channel_id,
        request.channel_url,
        request.channel_handle,
        request.search_query,
        request.max_videos,
        request.languages,
        request.refresh,
    )
    try:
        dump = service.fetch_transcript_dump(request)
    except Exception as exc:
        logger.exception("Transcript download request failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = f"{dump.channel_name.lower().replace(' ', '-')}-transcripts.json"
    logger.info(
        "Transcript download prepared filename=%s channel_id=%s transcripts_found=%s total_videos=%s",
        filename,
        dump.channel_id,
        dump.transcripts_found,
        len(dump.videos),
    )
    payload = json.dumps(dump.model_dump(mode="json"), indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/transcripts/analyze")
def analyze_transcript_dump(dump: TranscriptDumpResponse):
    logger.info(
        "Communication analysis request received channel_id=%s channel_name=%s total_videos=%s transcripts_found=%s",
        dump.channel_id,
        dump.channel_name,
        len(dump.videos),
        dump.transcripts_found,
    )
    try:
        report = analyzer.analyze_dump(dump)
        logger.info(
            "Communication analysis completed channel_id=%s transcripts_analyzed=%s total_word_count=%s",
            report.channel_id,
            report.transcripts_analyzed,
            report.total_word_count,
        )
        return report
    except Exception as exc:
        logger.exception("Communication analysis failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/channels/{channel_id}/transcripts/cached")
def get_cached_transcripts(
    channel_id: str,
    max_videos: int = Query(default=3, ge=1, le=50),
):
    logger.info(
        "Cached transcript request received channel_id=%s max_videos=%s",
        channel_id,
        max_videos,
    )
    try:
        dump = service.get_cached_transcripts(channel_id, max_videos)
        logger.info(
            "Cached transcript request completed channel_id=%s transcripts_found=%s total_videos=%s",
            dump.channel_id,
            dump.transcripts_found,
            len(dump.videos),
        )
        return dump
    except Exception as exc:
        logger.exception("Cached transcript request failed channel_id=%s: %s", channel_id, exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc

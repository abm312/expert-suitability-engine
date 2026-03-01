import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.core.config import get_settings
from app.schemas import TranscriptDumpRequest
from app.services.harvest_service import HarvestService


settings = get_settings()
service = HarvestService(settings)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "youtube_api_configured": bool(settings.YOUTUBE_API_KEY),
        "database_path": str(settings.database_path),
    }


@router.post("/transcripts/dump")
def create_transcript_dump(request: TranscriptDumpRequest):
    try:
        return service.fetch_transcript_dump(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/transcripts/download")
def download_transcript_dump(request: TranscriptDumpRequest):
    try:
        dump = service.fetch_transcript_dump(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = f"{dump.channel_name.lower().replace(' ', '-')}-transcripts.json"
    payload = json.dumps(dump.model_dump(mode="json"), indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/channels/{channel_id}/transcripts/cached")
def get_cached_transcripts(
    channel_id: str,
    max_videos: int = Query(default=10, ge=1, le=50),
):
    try:
        return service.get_cached_transcripts(channel_id, max_videos)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

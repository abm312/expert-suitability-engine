from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from typing import Optional, List, Dict, Any
import json
import asyncio
import logging
import traceback
import csv
import re
from datetime import datetime
from io import StringIO

from app.db.database import get_db
from app.db.models import RisingVoice
from app.core.config import get_settings
from app.core.rising_voices import (
    RISING_VOICES_FILTERS,
    RISING_VOICES_METRICS,
    RISING_VOICES_QUERIES,
)
from app.schemas.search import SearchRequest, DiscoverRequest, FilterConfig, MetricConfig, MetricType
from app.schemas.creator import CreatorResponse, CreatorDetail
from app.schemas.rising_voices import RisingVoiceResponse, RisingVoicesRefreshResponse, RisingVoiceScoreBreakdown
from app.services.creator_service import CreatorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()
creator_service = CreatorService()
settings = get_settings()

CURATED_EXPORT_QUERIES = [
    "AI/ML Engineer",
    "LLM Expert",
    "Data Scientist",
    "MLOps Specialist",
    "Computer Vision",
]

CURATED_EXPORT_METRICS = {
    MetricType.CREDIBILITY: MetricConfig(enabled=True, weight=0.25),
    MetricType.TOPIC_AUTHORITY: MetricConfig(enabled=True, weight=0.35),
    MetricType.COMMUNICATION: MetricConfig(enabled=False, weight=0.0),
    MetricType.FRESHNESS: MetricConfig(enabled=True, weight=0.20),
    MetricType.GROWTH: MetricConfig(enabled=True, weight=0.20),
}

CURATED_EXPORT_FILTERS = FilterConfig(
    subscriber_min=10000,
    uploads_last_90_days_min=2,
)

# Global progress tracker
search_progress = {"status": "idle", "step": "", "details": ""}


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Expert Suitability Engine"}


@router.get("/progress")
async def get_progress():
    """Get current search progress"""
    return search_progress


def update_progress(status: str, step: str, details: str = ""):
    """Update the global progress tracker"""
    global search_progress
    search_progress = {"status": status, "step": step, "details": details}


def require_rising_voices_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")
):
    expected = settings.RISING_VOICES_API_KEY
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


def _creator_export_fieldnames() -> List[str]:
    return [
        "name",
        "channel_url",
        "channel_id",
        "subscriber_count",
        "total_views",
        "overall_score",
        "niche_category",
        "topic_focus",
        "growth_trend",
        "growth_score",
        "credibility_score",
        "topic_authority_score",
        "freshness_score",
        "topic_match_summary",
        "description",
        "matched_queries",
        "top_video_titles",
    ]


def _write_creator_export_csv(rows: List[Dict[str, Any]]) -> str:
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=_creator_export_fieldnames())
    writer.writeheader()

    for row in rows:
        writer.writerow({
            "name": row.get("name"),
            "channel_url": row.get("channel_url"),
            "channel_id": row.get("channel_id"),
            "subscriber_count": row.get("subscriber_count"),
            "total_views": row.get("total_views"),
            "overall_score": row.get("overall_score"),
            "niche_category": row.get("niche_category"),
            "topic_focus": row.get("topic_focus"),
            "growth_trend": row.get("growth_trend"),
            "growth_score": row.get("growth_score"),
            "credibility_score": row.get("credibility_score"),
            "topic_authority_score": row.get("topic_authority_score"),
            "freshness_score": row.get("freshness_score"),
            "topic_match_summary": row.get("topic_match_summary"),
            "description": row.get("description"),
            "matched_queries": ", ".join(row.get("matched_queries", [])),
            "top_video_titles": " | ".join(
                video.get("title", "")
                for video in row.get("top_videos", [])
                if video.get("title")
            ),
        })

    return csv_buffer.getvalue()


def _export_filename(prefix: str, value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or prefix
    return f"{slug}.csv"


@router.post("/discover")
async def discover_creators(
    request: DiscoverRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Discover new creators by searching YouTube and adding to database.

    This is for populating the database with new creators to evaluate.
    """
    logger.info(f"🔍 DISCOVER REQUEST: query='{request.search_query}', max_results={request.max_results}")
    try:
        logger.info("Starting discovery process...")
        added = await creator_service.discover_creators(
            db,
            query=request.search_query,
            max_results=request.max_results,
        )
        logger.info(f"✅ Discovery complete: Added {len(added)} creators")
        return {
            "status": "success",
            "added_count": len(added),
            "creators": added,
        }
    except Exception as e:
        logger.error(f"❌ DISCOVER ERROR: {str(e)}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_creators(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Search and rank creators based on topic expertise.

    This is the main search endpoint that:
    1. Applies filters
    2. Scores creators on all enabled metrics
    3. Returns ranked creator cards with explanations
    """
    logger.info("=" * 80)
    logger.info(f"🔍 NEW SEARCH REQUEST RECEIVED")
    logger.info(f"Topic: '{request.topic_query}'")
    logger.info(f"Keywords: {request.topic_keywords}")
    logger.info(f"Limit: {request.limit}, Offset: {request.offset}")
    logger.info(f"Filters: {request.filters}")
    logger.info(f"Metrics: {[(m.value, f'weight={cfg.weight}, enabled={cfg.enabled}') for m, cfg in request.metrics.items()]}")
    logger.info("=" * 80)

    try:
        logger.info("Step 1: Updating progress to 'searching'...")
        update_progress("searching", "youtube", f"Searching YouTube for '{request.topic_query}'...")

        logger.info("Step 2: Calling creator_service.search_creators()...")
        results = await creator_service.search_creators(db, request, progress_callback=update_progress)

        logger.info(f"✅ SEARCH SUCCESSFUL!")
        logger.info(f"   - Discovered: {results.get('discovered_count', 0)} creators")
        logger.info(f"   - Filtered: {results.get('filtered_count', 0)} creators")
        logger.info(f"   - Returning: {len(results.get('creators', []))} creators")
        logger.info("=" * 80)

        update_progress("complete", "done", f"Found {results['filtered_count']} experts")
        return results

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ SEARCH FAILED WITH ERROR:")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        logger.error("=" * 80)
        update_progress("error", "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/export")
async def export_search_creators(
    request: SearchRequest,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export scored search results as structured JSON or CSV.

    This reuses the same search pipeline and metrics as the main search flow,
    but returns an editorial/content-friendly export format.
    """
    logger.info(
        "📦 EXPORT REQUEST: topic='%s' limit=%s offset=%s format=%s",
        request.topic_query,
        request.limit,
        request.offset,
        format,
    )

    try:
        results = await creator_service.search_creators(db, request)
        export_rows = creator_service.build_creator_export_rows(results)

        if format == "json":
            return {
                "query": request.topic_query,
                "exported_count": len(export_rows),
                "processing_time_ms": results.get("processing_time_ms"),
                "metrics_used": results.get("metrics_used", []),
                "creators": export_rows,
            }

        filename = _export_filename("creator-search", f"{request.topic_query}-creator-export")
        return StreamingResponse(
            iter([_write_creator_export_csv(export_rows)]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error("❌ EXPORT ERROR: %s", str(e))
        logger.error("Full traceback:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/export/curated")
async def export_curated_ai_creators(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    final_limit: int = Query(default=40, ge=1, le=100),
    per_query_limit: int = Query(default=10, ge=1, le=50),
    min_topic_authority: float = Query(default=0.7, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a cleaner editorial export by merging multiple AI-focused queries,
    applying stronger default filters, and deduplicating channels.
    """
    logger.info(
        "📦 CURATED EXPORT REQUEST: format=%s final_limit=%s per_query_limit=%s min_topic_authority=%s",
        format,
        final_limit,
        per_query_limit,
        min_topic_authority,
    )

    try:
        curated_rows = await creator_service.build_curated_export_rows(
            db=db,
            queries=CURATED_EXPORT_QUERIES,
            metrics=CURATED_EXPORT_METRICS,
            filters=CURATED_EXPORT_FILTERS,
            final_limit=final_limit,
            per_query_limit=per_query_limit,
            min_topic_authority=min_topic_authority,
        )

        if format == "json":
            return {
                "queries": CURATED_EXPORT_QUERIES,
                "exported_count": len(curated_rows),
                "default_filters": {
                    "subscriber_min": CURATED_EXPORT_FILTERS.subscriber_min,
                    "uploads_last_90_days_min": CURATED_EXPORT_FILTERS.uploads_last_90_days_min,
                },
                "min_topic_authority": min_topic_authority,
                "creators": curated_rows,
            }

        filename = _export_filename("ai-youtube-creators-export", f"ai-youtube-creators-export-{final_limit}")
        return StreamingResponse(
            iter([_write_creator_export_csv(curated_rows)]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error("❌ CURATED EXPORT ERROR: %s", str(e))
        logger.error("Full traceback:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/rising-voices/refresh",
    response_model=RisingVoicesRefreshResponse,
    dependencies=[Depends(require_rising_voices_api_key)],
)
async def refresh_rising_voices(
    db: AsyncSession = Depends(get_db),
):
    """
    Recompute the Rising AI Voices feed and store it in Postgres for fast serving.
    """
    logger.info(
        "📡 RISING VOICES REFRESH: final_limit=%s per_query_limit=%s min_topic_authority=%s",
        settings.RISING_VOICES_FINAL_LIMIT,
        settings.RISING_VOICES_PER_QUERY_LIMIT,
        settings.RISING_VOICES_MIN_TOPIC_AUTHORITY,
    )

    try:
        refresh_result = await creator_service.refresh_rising_voices_snapshot(
            db=db,
            queries=RISING_VOICES_QUERIES,
            metrics=RISING_VOICES_METRICS,
            filters=RISING_VOICES_FILTERS,
            final_limit=settings.RISING_VOICES_FINAL_LIMIT,
            per_query_limit=settings.RISING_VOICES_PER_QUERY_LIMIT,
            min_topic_authority=settings.RISING_VOICES_MIN_TOPIC_AUTHORITY,
        )

        return RisingVoicesRefreshResponse(
            status="success",
            refreshedAt=refresh_result["refreshed_at"],
            count=refresh_result["count"],
            endpoint="/api/v1/rising-voices",
            apiKeyRequired=bool(settings.RISING_VOICES_API_KEY),
        )

    except Exception as e:
        await db.rollback()
        logger.error("❌ RISING VOICES REFRESH ERROR: %s", str(e))
        logger.error("Full traceback:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/rising-voices",
    response_model=List[RisingVoiceResponse],
    dependencies=[Depends(require_rising_voices_api_key)],
)
async def get_rising_voices(
    db: AsyncSession = Depends(get_db),
):
    """
    Fast read endpoint for the precomputed Rising AI Voices feed.
    """
    result = await db.execute(
        select(RisingVoice)
        .order_by(RisingVoice.rank.asc(), RisingVoice.overall_score.desc())
    )
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No rising voices snapshot available yet. Run POST /api/v1/rising-voices/refresh first."
        )

    return [
        RisingVoiceResponse(
            name=row.name,
            slug=row.slug,
            host=row.host,
            subscriberCount=row.subscriber_count,
            growthSignal=row.growth_signal,
            scoreBreakdown=RisingVoiceScoreBreakdown(
                credibility=round(row.credibility_score or 0.0, 3),
                topicAuthority=round(row.topic_authority_score or 0.0, 3),
                communication=round(row.communication_score or 0.0, 3),
                freshness=round(row.freshness_score or 0.0, 3),
                growth=round(row.growth_score or 0.0, 3),
            ),
            overallScore=round(row.overall_score or 0.0, 3),
            tags=row.tags or [],
            channelUrl=row.channel_url,
            lastScored=row.last_scored,
        )
        for row in rows
    ]


@router.get("/creators")
async def list_creators(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="overall_score", regex="^(overall_score|total_subscribers|created_at)$"),
):
    """List all creators in the database"""
    from sqlalchemy import select, desc
    from app.db.models import Creator
    
    order_col = {
        "overall_score": Creator.overall_score,
        "total_subscribers": Creator.total_subscribers,
        "created_at": Creator.created_at,
    }.get(sort_by, Creator.overall_score)
    
    result = await db.execute(
        select(Creator)
        .order_by(desc(order_col))
        .offset(offset)
        .limit(limit)
    )
    creators = result.scalars().all()
    
    return {
        "creators": [
            {
                "id": c.id,
                "channel_id": c.channel_id,
                "channel_name": c.channel_name,
                "thumbnail_url": c.thumbnail_url,
                "total_subscribers": c.total_subscribers,
                "total_views": c.total_views,
                "overall_score": c.overall_score,
                "last_fetched_at": c.last_fetched_at,
            }
            for c in creators
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/creators/{creator_id}")
async def get_creator(
    creator_id: int,
    topic_query: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed creator information.
    
    If topic_query is provided, includes scoring and explanations.
    """
    creator = await creator_service.get_creator_detail(
        db,
        creator_id,
        topic_query=topic_query,
    )
    
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    return creator


@router.post("/creators/{creator_id}/refresh")
async def refresh_creator(
    creator_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Refresh creator data from YouTube API"""
    success = await creator_service.refresh_creator(db, creator_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Creator not found or refresh failed")
    
    return {"status": "success", "message": "Creator data refreshed"}


@router.get("/metrics")
async def get_available_metrics():
    """Get list of available metrics with descriptions"""
    return {
        "metrics": [
            {
                "id": "credibility",
                "name": "Credibility",
                "description": "Channel age, content depth, upload consistency, external validation",
                "default_weight": 0.2,
            },
            {
                "id": "topic_authority",
                "name": "Topic Authority",
                "description": "Alignment between content and target expertise topics",
                "default_weight": 0.3,
            },
            {
                "id": "communication",
                "name": "Communication Quality",
                "description": "Clarity, structure, and teaching effectiveness from transcripts",
                "default_weight": 0.2,
            },
            {
                "id": "freshness",
                "name": "Freshness",
                "description": "Recency of content and active publishing",
                "default_weight": 0.15,
            },
            {
                "id": "growth",
                "name": "Growth Trajectory",
                "description": "Subscriber growth and audience momentum",
                "default_weight": 0.15,
            },
        ]
    }


@router.get("/filters")
async def get_available_filters():
    """Get list of available filters with descriptions"""
    return {
        "filters": [
            {
                "id": "subscriber_min",
                "name": "Min Subscribers",
                "type": "number",
                "description": "Minimum subscriber count",
            },
            {
                "id": "subscriber_max",
                "name": "Max Subscribers",
                "type": "number",
                "description": "Maximum subscriber count",
            },
            {
                "id": "avg_video_length_min",
                "name": "Min Avg Video Length",
                "type": "number",
                "description": "Minimum average video length in seconds",
            },
            {
                "id": "growth_rate_min",
                "name": "Min Growth Rate",
                "type": "number",
                "description": "Minimum growth rate percentage",
            },
            {
                "id": "uploads_last_90_days_min",
                "name": "Min Recent Uploads",
                "type": "number",
                "description": "Minimum videos in last 90 days",
            },
            {
                "id": "topic_relevance_min",
                "name": "Min Topic Relevance",
                "type": "number",
                "description": "Minimum topic match score (0-1)",
            },
        ]
    }

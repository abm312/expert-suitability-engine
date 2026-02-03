from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import json
import asyncio

from app.db.database import get_db
from app.schemas.search import SearchRequest, DiscoverRequest
from app.schemas.creator import CreatorResponse, CreatorDetail
from app.services.creator_service import CreatorService

router = APIRouter()
creator_service = CreatorService()

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


@router.post("/discover")
async def discover_creators(
    request: DiscoverRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Discover new creators by searching YouTube and adding to database.
    
    This is for populating the database with new creators to evaluate.
    """
    try:
        added = await creator_service.discover_creators(
            db,
            query=request.search_query,
            max_results=request.max_results,
        )
        return {
            "status": "success",
            "added_count": len(added),
            "creators": added,
        }
    except Exception as e:
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
    try:
        update_progress("searching", "youtube", f"Searching YouTube for '{request.topic_query}'...")
        results = await creator_service.search_creators(db, request, progress_callback=update_progress)
        update_progress("complete", "done", f"Found {results['filtered_count']} experts")
        return results
    except Exception as e:
        update_progress("error", "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))


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


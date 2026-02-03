from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import re

from app.db.models import Creator, Video, Transcript, MetricsSnapshot
from app.services.youtube_service import YouTubeService
from app.services.embedding_service import EmbeddingService
from app.services.scoring_engine import ScoringEngine
from app.services.filter_service import FilterService
from app.services.explainability_service import ExplainabilityService
from app.schemas.search import SearchRequest, MetricType
from app.schemas.creator import CreatorCard, VideoSummary


def parse_datetime_safe(date_str: str) -> Optional[datetime]:
    """Safely parse datetime strings from YouTube API"""
    if not date_str:
        return None
    try:
        # Try standard ISO format first
        clean = date_str.replace("Z", "+00:00")
        # Handle microseconds with more than 6 digits
        clean = re.sub(r'\.(\d{6})\d+', r'.\1', clean)
        dt = datetime.fromisoformat(clean)
        return dt.replace(tzinfo=None)  # Make naive
    except Exception:
        try:
            # Try without microseconds
            clean = re.sub(r'\.\d+', '', date_str.replace("Z", ""))
            dt = datetime.fromisoformat(clean)
            return dt
        except Exception:
            return None


class CreatorService:
    """Main service for creator discovery, scoring, and retrieval"""
    
    def __init__(self):
        self.youtube = YouTubeService()
        self.embeddings = EmbeddingService()
        self.scoring = ScoringEngine()
        self.filters = FilterService()
        self.explainability = ExplainabilityService()
    
    async def discover_creators(
        self,
        db: AsyncSession,
        query: str,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Discover new creators via YouTube search and add to database.
        """
        # Search YouTube
        channels = await self.youtube.search_channels(query, max_results)
        
        added = []
        for channel in channels:
            channel_id = channel["channel_id"]
            
            # Check if already exists
            result = await db.execute(
                select(Creator).where(Creator.channel_id == channel_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                continue
            
            # Fetch full details
            details = await self.youtube.get_channel_details(channel_id)
            if not details:
                continue
            
            # Parse channel created date safely
            channel_created = parse_datetime_safe(details.get("channel_created_date"))
            
            # Create creator
            creator = Creator(
                channel_id=channel_id,
                channel_name=details["channel_name"],
                channel_description=details.get("channel_description"),
                total_subscribers=details.get("total_subscribers", 0),
                total_views=details.get("total_views", 0),
                total_videos=details.get("total_videos", 0),
                channel_created_date=channel_created,
                external_links=details.get("external_links", []),
                thumbnail_url=details.get("thumbnail_url"),
                country=details.get("country"),
                last_fetched_at=datetime.utcnow(),
            )
            db.add(creator)
            await db.flush()
            
            # Fetch videos
            videos_data = await self.youtube.get_channel_videos(channel_id, max_results=30)
            for v in videos_data:
                # Parse published date safely
                video_published = parse_datetime_safe(v.get("published_at"))
                
                video = Video(
                    creator_id=creator.id,
                    video_id=v["video_id"],
                    title=v["title"],
                    description=v.get("description"),
                    published_at=video_published,
                    duration_seconds=v.get("duration_seconds", 0),
                    views=v.get("views", 0),
                    likes=v.get("likes", 0),
                    comments=v.get("comments", 0),
                    has_captions=v.get("has_captions", False),
                    thumbnail_url=v.get("thumbnail_url"),
                    tags=v.get("tags", []),
                )
                db.add(video)
            
            # Create initial metrics snapshot
            snapshot = MetricsSnapshot(
                creator_id=creator.id,
                date=date.today(),
                subscriber_count=creator.total_subscribers,
                view_count=creator.total_views,
                video_count=creator.total_videos,
            )
            db.add(snapshot)
            
            added.append({
                "channel_id": channel_id,
                "channel_name": details["channel_name"],
                "subscribers": details.get("total_subscribers", 0),
            })
        
        await db.commit()
        return added
    
    async def search_creators(
        self,
        db: AsyncSession,
        request: SearchRequest,
        progress_callback: callable = None,
    ) -> Dict[str, Any]:
        """
        Search and rank creators based on topic and preferences.
        Auto-discovers new creators from YouTube based on the search query.
        """
        import time
        start_time = time.time()
        
        def update(status, step, details=""):
            if progress_callback:
                progress_callback(status, step, details)
        
        # Get topic embedding
        update("searching", "embedding", f"Looking for '{request.topic_query}' experts...")
        topic_embedding = None
        try:
            topic_embedding = await self.embeddings.embed_query(request.topic_query)
        except Exception:
            pass  # Fall back to keyword matching
        
        # AUTO-DISCOVER: Search YouTube for new creators (limited to 20 for speed)
        update("searching", "youtube", f"Searching YouTube for channels...")
        try:
            update("searching", "populating", "Fetching channel data and videos...")
            await self.discover_creators(db, request.topic_query, max_results=20)
        except Exception as e:
            print(f"Discovery error: {e}")
        
        # Fetch all creators with their data
        result = await db.execute(
            select(Creator)
            .options(
                selectinload(Creator.videos).selectinload(Video.transcript),
                selectinload(Creator.metrics_snapshots)
            )
        )
        creators = result.scalars().all()
        
        if not creators:
            return {
                "query": request.topic_query,
                "total_results": 0,
                "filtered_count": 0,
                "creators": [],
                "metrics_used": [],
                "filters_applied": {},
                "processing_time_ms": (time.time() - start_time) * 1000,
            }
        
        # Convert to dicts for processing
        creators_data = []
        for c in creators:
            creator_dict = {
                "id": c.id,
                "channel_id": c.channel_id,
                "channel_name": c.channel_name,
                "channel_description": c.channel_description,
                "total_subscribers": c.total_subscribers,
                "total_views": c.total_views,
                "total_videos": c.total_videos,
                "channel_created_date": c.channel_created_date,
                "external_links": c.external_links or [],
                "thumbnail_url": c.thumbnail_url,
                "videos": [
                    {
                        "video_id": v.video_id,
                        "title": v.title,
                        "description": v.description,
                        "published_at": v.published_at,
                        "duration_seconds": v.duration_seconds,
                        "views": v.views,
                        "likes": v.likes,
                        "comments": v.comments,
                        "has_captions": v.has_captions,
                        "thumbnail_url": v.thumbnail_url,
                        "tags": v.tags or [],
                        "transcript": {
                            "text": v.transcript.text if v.transcript else None,
                            "embedding": list(v.transcript.embedding) if v.transcript and v.transcript.embedding else None,
                        } if v.transcript else {}
                    }
                    for v in c.videos
                ],
                "metrics_snapshots": [
                    {
                        "date": s.date,
                        "subscriber_count": s.subscriber_count,
                        "view_count": s.view_count,
                        "video_count": s.video_count,
                    }
                    for s in c.metrics_snapshots
                ],
            }
            creators_data.append(creator_dict)
        
        total_count = len(creators_data)
        update("searching", "filtering", f"Checking {total_count} creators against your filters...")
        
        # Apply filters
        filtered_creators = self.filters.filter_creators(creators_data, request.filters)
        filtered_count = len(filtered_creators)
        
        update("searching", "scoring", f"Analyzing {filtered_count} potential experts...")
        
        # Score remaining creators
        scored_creators = []
        for i, creator_data in enumerate(filtered_creators):
            if i % 10 == 0:  # Update every 10 creators
                update("searching", "scoring", f"Evaluating expert {i+1} of {filtered_count}...")
            scoring_result = await self.scoring.score_creator(
                creator_data,
                request.metrics,
                topic_embedding=topic_embedding,
                topic_keywords=request.topic_keywords,
                embedding_service=self.embeddings,
            )
            
            # Generate explainability
            explanation = await self.explainability.generate_why_expert(
                creator_data,
                scoring_result,
                request.topic_query,
            )
            
            # Build creator card
            scored_creators.append({
                "creator_data": creator_data,
                "scoring_result": scoring_result,
                "explanation": explanation,
            })
        
        # Sort by overall score
        scored_creators.sort(
            key=lambda x: x["scoring_result"].overall_score,
            reverse=True
        )
        
        # Apply pagination
        paginated = scored_creators[request.offset:request.offset + request.limit]
        
        # Build response cards
        creator_cards = []
        for item in paginated:
            cd = item["creator_data"]
            sr = item["scoring_result"]
            exp = item["explanation"]
            
            # Get top videos
            top_videos = sorted(
                cd.get("videos", []),
                key=lambda v: v.get("views", 0),
                reverse=True
            )[:3]
            
            card = {
                "id": cd["id"],
                "channel_id": cd["channel_id"],
                "channel_name": cd["channel_name"],
                "thumbnail_url": cd.get("thumbnail_url"),
                "total_subscribers": cd["total_subscribers"],
                "total_views": cd["total_views"],
                "overall_score": round(sr.overall_score, 3),
                "subscores": {k: round(v.score, 3) for k, v in sr.metric_scores.items()},
                "why_expert": exp["bullets"],
                "topic_match_summary": f"Strong match for '{request.topic_query}'" if sr.overall_score > 0.7 else f"Relevant to '{request.topic_query}'",
                "top_videos": [
                    {
                        "video_id": v["video_id"],
                        "title": v["title"],
                        "views": v["views"],
                        "thumbnail_url": v.get("thumbnail_url"),
                    }
                    for v in top_videos
                ],
                "relevant_content": exp["relevant_content"],
                "suggested_topics": exp["suggested_topics"],
                "growth_trend": self._determine_growth_trend(sr),
                "external_links": cd.get("external_links", [])[:5],
                "channel_url": f"https://youtube.com/channel/{cd['channel_id']}",
            }
            creator_cards.append(card)
        
        # Get active metrics
        active_metrics = [
            m.value for m, cfg in request.metrics.items() 
            if cfg.enabled
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "query": request.topic_query,
            "total_results": total_count,
            "filtered_count": filtered_count,
            "creators": creator_cards,
            "metrics_used": active_metrics,
            "filters_applied": self.filters.get_filter_summary(request.filters),
            "processing_time_ms": round(processing_time, 2),
        }
    
    def _determine_growth_trend(self, scoring_result) -> str:
        """Determine growth trend description"""
        if "growth" not in scoring_result.metric_scores:
            return "Unknown"
        
        growth = scoring_result.metric_scores["growth"]
        if not growth.available:
            return "Insufficient data"
        
        if growth.score >= 0.8:
            return "Rapid growth"
        elif growth.score >= 0.6:
            return "Steady growth"
        elif growth.score >= 0.4:
            return "Stable"
        elif growth.score >= 0.2:
            return "Slowing"
        else:
            return "Declining"
    
    async def get_creator_detail(
        self,
        db: AsyncSession,
        creator_id: int,
        topic_query: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get detailed creator information with full scoring"""
        result = await db.execute(
            select(Creator)
            .options(
                selectinload(Creator.videos).selectinload(Video.transcript),
                selectinload(Creator.metrics_snapshots)
            )
            .where(Creator.id == creator_id)
        )
        creator = result.scalar_one_or_none()
        
        if not creator:
            return None
        
        # Convert to dict
        creator_data = {
            "id": creator.id,
            "channel_id": creator.channel_id,
            "channel_name": creator.channel_name,
            "channel_description": creator.channel_description,
            "total_subscribers": creator.total_subscribers,
            "total_views": creator.total_views,
            "total_videos": creator.total_videos,
            "channel_created_date": creator.channel_created_date,
            "external_links": creator.external_links or [],
            "thumbnail_url": creator.thumbnail_url,
            "country": creator.country,
            "created_at": creator.created_at,
            "last_fetched_at": creator.last_fetched_at,
            "videos": [
                {
                    "video_id": v.video_id,
                    "title": v.title,
                    "description": v.description,
                    "published_at": v.published_at,
                    "duration_seconds": v.duration_seconds,
                    "views": v.views,
                    "likes": v.likes,
                    "comments": v.comments,
                    "has_captions": v.has_captions,
                    "thumbnail_url": v.thumbnail_url,
                    "tags": v.tags or [],
                    "transcript": {
                        "text": v.transcript.text if v.transcript else None,
                    } if v.transcript else {}
                }
                for v in creator.videos
            ],
            "metrics_snapshots": [
                {
                    "date": str(s.date),
                    "subscriber_count": s.subscriber_count,
                    "view_count": s.view_count,
                    "video_count": s.video_count,
                }
                for s in sorted(creator.metrics_snapshots, key=lambda x: x.date)
            ],
        }
        
        # Compute scores if topic provided
        if topic_query:
            topic_embedding = await self.embeddings.embed_query(topic_query)
            default_metrics = {
                MetricType.CREDIBILITY: {"enabled": True, "weight": 0.2},
                MetricType.TOPIC_AUTHORITY: {"enabled": True, "weight": 0.3},
                MetricType.COMMUNICATION: {"enabled": True, "weight": 0.2},
                MetricType.FRESHNESS: {"enabled": True, "weight": 0.15},
                MetricType.GROWTH: {"enabled": True, "weight": 0.15},
            }
            from app.schemas.search import MetricConfig
            metrics = {k: MetricConfig(**v) for k, v in default_metrics.items()}
            
            scoring_result = await self.scoring.score_creator(
                creator_data,
                metrics,
                topic_embedding=topic_embedding,
                embedding_service=self.embeddings,
            )
            
            explanation = await self.explainability.generate_why_expert(
                creator_data,
                scoring_result,
                topic_query,
            )
            
            creator_data["scoring"] = scoring_result.to_dict()
            creator_data["explanation"] = explanation
        
        return creator_data
    
    async def refresh_creator(
        self,
        db: AsyncSession,
        creator_id: int,
    ) -> bool:
        """Refresh creator data from YouTube"""
        result = await db.execute(
            select(Creator).where(Creator.id == creator_id)
        )
        creator = result.scalar_one_or_none()
        
        if not creator:
            return False
        
        # Fetch fresh data
        details = await self.youtube.get_channel_details(creator.channel_id)
        if not details:
            return False
        
        # Update creator
        creator.channel_name = details["channel_name"]
        creator.channel_description = details.get("channel_description")
        creator.total_subscribers = details.get("total_subscribers", 0)
        creator.total_views = details.get("total_views", 0)
        creator.total_videos = details.get("total_videos", 0)
        creator.external_links = details.get("external_links", [])
        creator.thumbnail_url = details.get("thumbnail_url")
        creator.last_fetched_at = datetime.utcnow()
        
        # Add metrics snapshot
        snapshot = MetricsSnapshot(
            creator_id=creator.id,
            date=date.today(),
            subscriber_count=creator.total_subscribers,
            view_count=creator.total_views,
            video_count=creator.total_videos,
        )
        db.add(snapshot)
        
        await db.commit()
        return True


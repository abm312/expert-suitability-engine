from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import re
import logging
import traceback

from app.db.models import Creator, Video, Transcript, MetricsSnapshot
from app.services.youtube_service import YouTubeService
from app.services.embedding_service import EmbeddingService
from app.services.scoring_engine import ScoringEngine
from app.services.filter_service import FilterService
from app.services.explainability_service import ExplainabilityService
from app.schemas.search import SearchRequest, MetricType
from app.schemas.creator import CreatorCard, VideoSummary

logger = logging.getLogger(__name__)


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
        logger.info(f"📺 DISCOVER: Searching YouTube for '{query}' (max {max_results} results)")

        try:
            # Search YouTube
            logger.info("   → Calling YouTube API search_channels()...")
            channels = await self.youtube.search_channels(query, max_results)
            logger.info(f"   ✓ Found {len(channels)} channels from YouTube")

            added = []
            logger.info(f"   → Processing {len(channels)} channels...")

            for idx, channel in enumerate(channels, 1):
                channel_id = channel["channel_id"]
                channel_name = channel.get("channel_name", "Unknown")
                logger.info(f"   [{idx}/{len(channels)}] Processing: {channel_name} ({channel_id})")

                # Check if already exists
                result = await db.execute(
                    select(Creator).where(Creator.channel_id == channel_id)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    logger.info(f"      ↷ Already in database, skipping")
                    continue

                # Fetch full details
                logger.info(f"      → Fetching channel details...")
                details = await self.youtube.get_channel_details(channel_id)
                if not details:
                    logger.warning(f"      ⚠ Failed to get channel details, skipping")
                    continue
                logger.info(f"      ✓ Got details: {details.get('total_subscribers', 0)} subscribers")


                # Parse channel created date safely
                channel_created = parse_datetime_safe(details.get("channel_created_date"))

                # Create creator
                logger.info(f"      → Creating creator in database...")
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
                logger.info(f"      ✓ Creator saved (ID: {creator.id})")

                # Fetch videos
                logger.info(f"      → Fetching videos (up to 30)...")
                videos_data = await self.youtube.get_channel_videos(channel_id, max_results=30)
                logger.info(f"      ✓ Got {len(videos_data)} videos")

                # Process each video
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

                logger.info(f"      → Saved {len(videos_data)} videos and metrics snapshot")
                added.append({
                    "channel_id": channel_id,
                    "channel_name": details["channel_name"],
                    "subscribers": details.get("total_subscribers", 0),
                })
                logger.info(f"      ✓ Channel fully processed!")

            logger.info(f"   → Committing {len(added)} new creators to database...")
            await db.commit()
            logger.info(f"✅ DISCOVER COMPLETE: Added {len(added)} new creators")
            return added

        except Exception as e:
            logger.error(f"❌ DISCOVER ERROR: {str(e)}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            await db.rollback()
            raise
    
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
        logger.info("🔎 SEARCH_CREATORS: Starting search flow")

        def update(status, step, details=""):
            if progress_callback:
                progress_callback(status, step, details)

        try:
            # Get topic embedding
            logger.info(f"Step 1: Getting embedding for '{request.topic_query}'")
            update("searching", "embedding", f"Looking for '{request.topic_query}' experts...")
            topic_embedding = None
            try:
                topic_embedding = await self.embeddings.embed_query(request.topic_query)
                logger.info(f"   ✓ Got embedding (length: {len(topic_embedding) if topic_embedding else 0})")
            except Exception as e:
                logger.warning(f"   ⚠ Embedding failed: {e}, falling back to keyword matching")
                pass  # Fall back to keyword matching

            # AUTO-DISCOVER: Search YouTube for new creators (limited to 20 for speed)
            logger.info(f"Step 2: Auto-discovering creators from YouTube")
            update("searching", "youtube", f"Searching YouTube for channels...")
            try:
                update("searching", "populating", "Fetching channel data and videos...")
                await self.discover_creators(db, request.topic_query, max_results=20)
                logger.info(f"   ✓ Discovery completed")
            except Exception as e:
                logger.error(f"   ❌ Discovery error: {e}")
                logger.error(f"   Traceback:\n{traceback.format_exc()}")
                # Continue anyway with existing creators in DB


            # Fetch all creators with their data
            logger.info(f"Step 3: Fetching all creators from database with videos and metrics")
            result = await db.execute(
                select(Creator)
                .options(
                    selectinload(Creator.videos).selectinload(Video.transcript),
                    selectinload(Creator.metrics_snapshots)
                )
            )
            creators = result.scalars().all()
            logger.info(f"   ✓ Fetched {len(creators)} creators from database")

            if not creators:
                logger.warning(f"   ⚠ No creators in database, returning empty results")
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
            logger.info(f"Step 4: Converting {len(creators)} creators to data format")
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
            logger.info(f"   ✓ Converted {total_count} creators")

            logger.info(f"Step 5: Applying filters")
            logger.info(f"   Filters: {request.filters}")
            update("searching", "filtering", f"Checking {total_count} creators against your filters...")

            # Apply filters
            filtered_creators = self.filters.filter_creators(creators_data, request.filters)
            filtered_count = len(filtered_creators)
            logger.info(f"   ✓ {filtered_count} creators passed filters (filtered out {total_count - filtered_count})")

            logger.info(f"Step 6: Scoring {filtered_count} creators")
            update("searching", "scoring", f"Analyzing {filtered_count} potential experts...")


            # Score remaining creators
            scored_creators = []
            for i, creator_data in enumerate(filtered_creators):
                if i % 10 == 0:  # Update every 10 creators
                    update("searching", "scoring", f"Evaluating expert {i+1} of {filtered_count}...")
                    logger.info(f"   Scoring creator {i+1}/{filtered_count}: {creator_data.get('channel_name')}")

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

            logger.info(f"   ✓ Scored all {len(scored_creators)} creators")


            logger.info(f"Step 7: Sorting and paginating results")
            # Sort by overall score
            scored_creators.sort(
                key=lambda x: x["scoring_result"].overall_score,
                reverse=True
            )
            logger.info(f"   ✓ Sorted by score (top score: {scored_creators[0]['scoring_result'].overall_score if scored_creators else 0:.3f})")

            # Apply pagination
            paginated = scored_creators[request.offset:request.offset + request.limit]
            logger.info(f"   ✓ Paginated: returning {len(paginated)} creators (offset {request.offset}, limit {request.limit})")

            logger.info(f"Step 8: Building response cards")
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


            logger.info(f"   ✓ Built {len(creator_cards)} creator cards")

            # Get active metrics
            active_metrics = [
                m.value for m, cfg in request.metrics.items()
                if cfg.enabled
            ]

            processing_time = (time.time() - start_time) * 1000

            logger.info("=" * 80)
            logger.info(f"✅ SEARCH COMPLETE!")
            logger.info(f"   Total discovered: {total_count}")
            logger.info(f"   Passed filters: {filtered_count}")
            logger.info(f"   Returning: {len(creator_cards)} creators")
            logger.info(f"   Processing time: {processing_time:.2f}ms")
            logger.info(f"   Active metrics: {active_metrics}")
            logger.info("=" * 80)

            return {
                "query": request.topic_query,
                "total_results": total_count,
                "discovered_count": total_count,  # Add this for routes.py logging
                "filtered_count": filtered_count,
                "creators": creator_cards,
                "metrics_used": active_metrics,
                "filters_applied": self.filters.get_filter_summary(request.filters),
                "processing_time_ms": round(processing_time, 2),
            }

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ SEARCH_CREATORS FAILED")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error message: {str(e)}")
            logger.error(f"   Full traceback:\n{traceback.format_exc()}")
            logger.error("=" * 80)
            raise
    
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


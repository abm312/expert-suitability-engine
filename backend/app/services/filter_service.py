from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from statistics import mean
from app.schemas.search import FilterConfig


class FilterService:
    """
    Filter Service
    
    Applies hard constraints before scoring.
    Filters run BEFORE scoring to reduce computation.
    """
    
    def filter_creators(
        self,
        creators_data: List[Dict[str, Any]],
        filters: FilterConfig,
    ) -> List[Dict[str, Any]]:
        """
        Apply all enabled filters to a list of creators.
        
        Returns only creators that pass ALL filters.
        """
        filtered = []
        
        for creator in creators_data:
            if self._passes_all_filters(creator, filters):
                filtered.append(creator)
        
        return filtered
    
    def _passes_all_filters(
        self,
        creator: Dict[str, Any],
        filters: FilterConfig,
    ) -> bool:
        """Check if a creator passes all filter criteria"""
        
        # Subscriber count filter
        if filters.subscriber_min is not None:
            if creator.get("total_subscribers", 0) < filters.subscriber_min:
                return False
        
        if filters.subscriber_max is not None:
            if creator.get("total_subscribers", 0) > filters.subscriber_max:
                return False
        
        # Average video length filter
        if filters.avg_video_length_min is not None:
            avg_length = self._get_avg_video_length(creator)
            if avg_length < filters.avg_video_length_min:
                return False
        
        # Growth rate filter
        if filters.growth_rate_min is not None:
            growth_rate = self._get_growth_rate(creator)
            if growth_rate is None or growth_rate < filters.growth_rate_min:
                return False
        
        # Recent uploads filter
        if filters.uploads_last_90_days_min is not None:
            recent_count = self._count_recent_uploads(creator, days=90)
            if recent_count < filters.uploads_last_90_days_min:
                return False
        
        # Topic relevance filter (requires pre-computed score)
        if filters.topic_relevance_min is not None:
            topic_score = creator.get("topic_score", 0)
            if topic_score < filters.topic_relevance_min:
                return False
        
        return True
    
    def _get_avg_video_length(self, creator: Dict[str, Any]) -> float:
        """Calculate average video length in seconds"""
        videos = creator.get("videos", [])
        if not videos:
            return 0
        
        durations = [v.get("duration_seconds", 0) for v in videos if v.get("duration_seconds", 0) > 60]
        if not durations:
            return 0
        
        return mean(durations)
    
    def _get_growth_rate(self, creator: Dict[str, Any]) -> Optional[float]:
        """Get growth rate from metrics snapshots"""
        snapshots = creator.get("metrics_snapshots", [])
        if len(snapshots) < 2:
            return None
        
        # Sort by date
        sorted_snapshots = sorted(
            snapshots,
            key=lambda x: x.get("date", "")
        )
        
        oldest = sorted_snapshots[0].get("subscriber_count", 0)
        latest = sorted_snapshots[-1].get("subscriber_count", 0)
        
        if oldest == 0:
            return None
        
        return ((latest - oldest) / oldest) * 100
    
    def _count_recent_uploads(self, creator: Dict[str, Any], days: int = 90) -> int:
        """Count videos uploaded in the last N days"""
        videos = creator.get("videos", [])
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = 0
        
        for video in videos:
            pub_date = video.get("published_at")
            if pub_date:
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                if pub_date.replace(tzinfo=None) > cutoff:
                    count += 1
        
        return count
    
    def get_filter_summary(self, filters: FilterConfig) -> Dict[str, Any]:
        """Get a summary of active filters for display"""
        active = {}
        
        if filters.subscriber_min is not None:
            active["subscriber_min"] = filters.subscriber_min
        if filters.subscriber_max is not None:
            active["subscriber_max"] = filters.subscriber_max
        if filters.avg_video_length_min is not None:
            active["avg_video_length_min"] = f"{filters.avg_video_length_min // 60} min"
        if filters.growth_rate_min is not None:
            active["growth_rate_min"] = f"{filters.growth_rate_min}%"
        if filters.uploads_last_90_days_min is not None:
            active["uploads_last_90_days_min"] = filters.uploads_last_90_days_min
        if filters.topic_relevance_min is not None:
            active["topic_relevance_min"] = filters.topic_relevance_min
        
        return active


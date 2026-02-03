from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from app.metrics.base import BaseMetric, MetricResult


class FreshnessMetric(BaseMetric):
    """
    Freshness Module
    
    Measures how current and active the creator's content is.
    
    Signals:
    - % of videos published in last 90 days
    - Topic relevance in recent content
    - Recency of last upload
    
    Output:
    - freshness_score ∈ [0,1]
    """
    
    name = "freshness"
    description = "Measures how current and actively updated the creator's content is"
    
    def available(self, creator_data: Dict[str, Any]) -> bool:
        """Freshness can be computed if we have videos with publish dates"""
        videos = creator_data.get("videos", [])
        for video in videos:
            if video.get("published_at"):
                return True
        return False
    
    async def compute(
        self,
        creator_data: Dict[str, Any],
        topic_embedding: Optional[List[float]] = None,
        **kwargs
    ) -> MetricResult:
        if not self.available(creator_data):
            return MetricResult(
                score=0.0,
                available=False,
                factors=["No video publish dates available"]
            )
        
        videos = creator_data.get("videos", [])
        now = datetime.utcnow()
        
        factors = []
        scores = []
        
        # 1. Recent activity score (% of videos in last 90 days)
        recent_score, recent_factor = self._compute_recent_activity(videos, now)
        scores.append(recent_score * 0.4)
        factors.append(recent_factor)
        
        # 2. Last upload recency
        recency_score, recency_factor = self._compute_last_upload_recency(videos, now)
        scores.append(recency_score * 0.35)
        factors.append(recency_factor)
        
        # 3. Upload momentum (accelerating or decelerating)
        momentum_score, momentum_factor = self._compute_upload_momentum(videos, now)
        scores.append(momentum_score * 0.25)
        factors.append(momentum_factor)
        
        total_score = sum(scores)
        
        return MetricResult(
            score=total_score,
            available=True,
            factors=factors,
            raw_data={
                "recent_activity_score": recent_score,
                "recency_score": recency_score,
                "momentum_score": momentum_score,
            }
        )
    
    def _parse_date(self, date_val) -> Optional[datetime]:
        """Parse various date formats"""
        if date_val is None:
            return None
        if isinstance(date_val, datetime):
            return date_val.replace(tzinfo=None)
        if isinstance(date_val, str):
            try:
                return datetime.fromisoformat(date_val.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                return None
        return None
    
    def _compute_recent_activity(
        self,
        videos: List[Dict[str, Any]],
        now: datetime
    ) -> tuple[float, str]:
        """Calculate percentage of videos from last 90 days"""
        ninety_days_ago = now - timedelta(days=90)
        
        total_videos = 0
        recent_videos = 0
        
        for video in videos:
            pub_date = self._parse_date(video.get("published_at"))
            if pub_date:
                total_videos += 1
                if pub_date > ninety_days_ago:
                    recent_videos += 1
        
        if total_videos == 0:
            return 0.0, "No dated videos found"
        
        recent_percentage = recent_videos / total_videos
        
        # Also consider absolute number
        if recent_videos >= 10:
            score = min(1.0, 0.7 + recent_percentage * 0.3)
            factor = f"Very active: {recent_videos} videos in last 90 days"
        elif recent_videos >= 5:
            score = 0.6 + recent_percentage * 0.3
            factor = f"Active: {recent_videos} videos in last 90 days"
        elif recent_videos >= 2:
            score = 0.4 + recent_percentage * 0.3
            factor = f"Moderately active: {recent_videos} videos in last 90 days"
        elif recent_videos == 1:
            score = 0.3
            factor = "1 video in last 90 days"
        else:
            score = 0.1
            factor = "No videos in last 90 days"
        
        return score, factor
    
    def _compute_last_upload_recency(
        self,
        videos: List[Dict[str, Any]],
        now: datetime
    ) -> tuple[float, str]:
        """Score based on how recent the last upload was"""
        latest_date = None
        
        for video in videos:
            pub_date = self._parse_date(video.get("published_at"))
            if pub_date:
                if latest_date is None or pub_date > latest_date:
                    latest_date = pub_date
        
        if latest_date is None:
            return 0.0, "Cannot determine last upload date"
        
        days_since_upload = (now - latest_date).days
        
        if days_since_upload <= 7:
            score = 1.0
            factor = f"Very recent upload ({days_since_upload} days ago)"
        elif days_since_upload <= 14:
            score = 0.9
            factor = f"Recent upload ({days_since_upload} days ago)"
        elif days_since_upload <= 30:
            score = 0.75
            factor = f"Upload within last month"
        elif days_since_upload <= 60:
            score = 0.5
            factor = f"Last upload {days_since_upload} days ago"
        elif days_since_upload <= 90:
            score = 0.3
            factor = f"Last upload ~{days_since_upload // 30} months ago"
        else:
            score = 0.1
            factor = f"Inactive for {days_since_upload // 30}+ months"
        
        return score, factor
    
    def _compute_upload_momentum(
        self,
        videos: List[Dict[str, Any]],
        now: datetime
    ) -> tuple[float, str]:
        """Compare recent vs older upload frequency"""
        ninety_days_ago = now - timedelta(days=90)
        one_eighty_days_ago = now - timedelta(days=180)
        
        recent_count = 0  # 0-90 days
        older_count = 0   # 90-180 days
        
        for video in videos:
            pub_date = self._parse_date(video.get("published_at"))
            if pub_date:
                if pub_date > ninety_days_ago:
                    recent_count += 1
                elif pub_date > one_eighty_days_ago:
                    older_count += 1
        
        if older_count == 0 and recent_count == 0:
            return 0.5, "Insufficient upload history for momentum"
        
        if older_count == 0:
            if recent_count > 0:
                return 1.0, "New or ramping up activity"
            return 0.5, "Limited activity data"
        
        # Calculate momentum ratio
        momentum_ratio = recent_count / older_count
        
        if momentum_ratio > 1.5:
            score = 1.0
            factor = f"Accelerating uploads ({recent_count} vs {older_count})"
        elif momentum_ratio > 1.0:
            score = 0.8
            factor = "Increasing upload frequency"
        elif momentum_ratio > 0.7:
            score = 0.6
            factor = "Stable upload frequency"
        elif momentum_ratio > 0.3:
            score = 0.4
            factor = "Slowing upload frequency"
        else:
            score = 0.2
            factor = f"Declining activity ({recent_count} vs {older_count})"
        
        return score, factor


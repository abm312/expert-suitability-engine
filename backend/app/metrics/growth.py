from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, date
from app.metrics.base import BaseMetric, MetricResult


class GrowthMetric(BaseMetric):
    """
    Growth Trajectory Module
    
    Measures channel growth momentum and trajectory.
    
    Signals:
    - Subscriber growth (30/90/180 days)
    - Growth acceleration (is growth speeding up?)
    - View growth trends
    
    Output:
    - growth_score ∈ [0,1]
    - growth_rate (percentage)
    """
    
    name = "growth"
    description = "Measures channel growth trajectory and momentum"
    
    def available(self, creator_data: Dict[str, Any]) -> bool:
        """Growth requires metrics snapshots or at least current subscriber data"""
        # Can compute basic growth from video performance even without snapshots
        has_snapshots = len(creator_data.get("metrics_snapshots", [])) >= 2
        has_subscribers = creator_data.get("total_subscribers", 0) > 0
        return has_snapshots or has_subscribers
    
    async def compute(self, creator_data: Dict[str, Any], **kwargs) -> MetricResult:
        if not self.available(creator_data):
            return MetricResult(
                score=0.0,
                available=False,
                factors=["Insufficient data for growth analysis"]
            )
        
        factors = []
        scores = []
        raw_data = {}
        
        snapshots = creator_data.get("metrics_snapshots", [])
        
        if len(snapshots) >= 2:
            # Use snapshots for accurate growth calculation
            growth_score, growth_factor, growth_rate = self._compute_snapshot_growth(snapshots)
            scores.append(growth_score * 0.5)
            factors.append(growth_factor)
            raw_data["growth_rate"] = growth_rate
            
            # Acceleration
            accel_score, accel_factor = self._compute_acceleration(snapshots)
            scores.append(accel_score * 0.3)
            factors.append(accel_factor)
        else:
            # Estimate from current stats and video performance
            est_score, est_factor = self._estimate_growth_from_videos(creator_data)
            scores.append(est_score * 0.6)
            factors.append(est_factor)
        
        # Video performance trend
        video_score, video_factor = self._compute_video_performance_trend(creator_data)
        scores.append(video_score * 0.2)
        factors.append(video_factor)
        
        total_score = sum(scores)
        
        return MetricResult(
            score=total_score,
            available=True,
            factors=factors,
            raw_data=raw_data
        )
    
    def _parse_date(self, date_val) -> Optional[date]:
        """Parse date from various formats"""
        if date_val is None:
            return None
        if isinstance(date_val, date):
            return date_val
        if isinstance(date_val, datetime):
            return date_val.date()
        if isinstance(date_val, str):
            try:
                dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                return dt.date()
            except ValueError:
                return None
        return None
    
    def _compute_snapshot_growth(
        self,
        snapshots: List[Dict[str, Any]]
    ) -> tuple[float, str, float]:
        """Calculate growth from metrics snapshots"""
        # Sort by date
        sorted_snapshots = sorted(
            snapshots,
            key=lambda x: self._parse_date(x.get("date")) or date.min
        )
        
        if len(sorted_snapshots) < 2:
            return 0.5, "Insufficient snapshot history", 0.0
        
        latest = sorted_snapshots[-1]
        
        # Find snapshot from ~90 days ago
        target_date = date.today() - timedelta(days=90)
        older_snapshot = None
        
        for snap in sorted_snapshots:
            snap_date = self._parse_date(snap.get("date"))
            if snap_date and snap_date <= target_date:
                older_snapshot = snap
        
        if older_snapshot is None:
            older_snapshot = sorted_snapshots[0]
        
        latest_subs = latest.get("subscriber_count", 0)
        older_subs = older_snapshot.get("subscriber_count", 0)
        
        if older_subs == 0:
            return 0.5, "Cannot calculate growth rate", 0.0
        
        growth_rate = ((latest_subs - older_subs) / older_subs) * 100
        
        # Score based on growth rate
        if growth_rate > 50:
            score = 1.0
            factor = f"Exceptional growth: +{growth_rate:.1f}% subscribers"
        elif growth_rate > 25:
            score = 0.85
            factor = f"Strong growth: +{growth_rate:.1f}% subscribers"
        elif growth_rate > 10:
            score = 0.7
            factor = f"Good growth: +{growth_rate:.1f}% subscribers"
        elif growth_rate > 5:
            score = 0.5
            factor = f"Moderate growth: +{growth_rate:.1f}% subscribers"
        elif growth_rate > 0:
            score = 0.35
            factor = f"Slow growth: +{growth_rate:.1f}% subscribers"
        elif growth_rate > -5:
            score = 0.2
            factor = f"Flat/slight decline: {growth_rate:.1f}%"
        else:
            score = 0.1
            factor = f"Declining: {growth_rate:.1f}% subscribers"
        
        return score, factor, growth_rate
    
    def _compute_acceleration(
        self,
        snapshots: List[Dict[str, Any]]
    ) -> tuple[float, str]:
        """Check if growth is accelerating or decelerating"""
        if len(snapshots) < 3:
            return 0.5, "Insufficient data for acceleration analysis"
        
        sorted_snapshots = sorted(
            snapshots,
            key=lambda x: self._parse_date(x.get("date")) or date.min
        )
        
        # Calculate recent growth vs older growth
        mid_point = len(sorted_snapshots) // 2
        
        older_subs = [s.get("subscriber_count", 0) for s in sorted_snapshots[:mid_point]]
        newer_subs = [s.get("subscriber_count", 0) for s in sorted_snapshots[mid_point:]]
        
        if not older_subs or not newer_subs or older_subs[0] == 0:
            return 0.5, "Cannot compute acceleration"
        
        older_growth = (older_subs[-1] - older_subs[0]) / older_subs[0] if older_subs[0] > 0 else 0
        newer_growth = (newer_subs[-1] - newer_subs[0]) / newer_subs[0] if newer_subs[0] > 0 else 0
        
        if older_growth == 0:
            if newer_growth > 0:
                return 0.8, "Growth accelerating from flat"
            return 0.5, "Stable (no growth)"
        
        acceleration = (newer_growth - older_growth) / abs(older_growth)
        
        if acceleration > 0.5:
            score = 1.0
            factor = "Growth accelerating significantly"
        elif acceleration > 0.1:
            score = 0.75
            factor = "Growth accelerating"
        elif acceleration > -0.1:
            score = 0.5
            factor = "Stable growth trajectory"
        elif acceleration > -0.5:
            score = 0.3
            factor = "Growth slowing"
        else:
            score = 0.15
            factor = "Growth decelerating"
        
        return score, factor
    
    def _estimate_growth_from_videos(
        self,
        creator_data: Dict[str, Any]
    ) -> tuple[float, str]:
        """Estimate growth potential from video performance"""
        videos = creator_data.get("videos", [])
        total_subs = creator_data.get("total_subscribers", 0)
        
        if not videos or total_subs == 0:
            return 0.5, "Limited data for growth estimation"
        
        # Calculate average views per video relative to subscriber count
        total_views = sum(v.get("views", 0) for v in videos)
        avg_views = total_views / len(videos) if videos else 0
        
        # View-to-subscriber ratio (higher = more discoverable/growing)
        view_ratio = avg_views / total_subs if total_subs > 0 else 0
        
        if view_ratio > 0.5:
            score = 0.9
            factor = "High view-to-subscriber ratio indicates growth"
        elif view_ratio > 0.2:
            score = 0.7
            factor = "Healthy view engagement suggests steady growth"
        elif view_ratio > 0.1:
            score = 0.5
            factor = "Moderate engagement levels"
        else:
            score = 0.3
            factor = "Lower view engagement"
        
        return score, factor
    
    def _compute_video_performance_trend(
        self,
        creator_data: Dict[str, Any]
    ) -> tuple[float, str]:
        """Analyze if recent videos perform better than older ones"""
        videos = creator_data.get("videos", [])
        
        if len(videos) < 4:
            return 0.5, "Too few videos for trend analysis"
        
        # Sort by publish date
        dated_videos = []
        for v in videos:
            pub_date = v.get("published_at")
            if pub_date:
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                dated_videos.append((pub_date, v.get("views", 0)))
        
        if len(dated_videos) < 4:
            return 0.5, "Insufficient dated videos"
        
        sorted_videos = sorted(dated_videos, key=lambda x: x[0])
        
        # Compare recent half vs older half
        mid = len(sorted_videos) // 2
        older_avg = sum(v[1] for v in sorted_videos[:mid]) / mid
        newer_avg = sum(v[1] for v in sorted_videos[mid:]) / (len(sorted_videos) - mid)
        
        if older_avg == 0:
            if newer_avg > 0:
                return 0.8, "Recent videos gaining traction"
            return 0.5, "Limited view data"
        
        trend_ratio = newer_avg / older_avg
        
        if trend_ratio > 1.5:
            score = 1.0
            factor = "Recent videos significantly outperforming"
        elif trend_ratio > 1.1:
            score = 0.75
            factor = "Recent videos performing better"
        elif trend_ratio > 0.9:
            score = 0.5
            factor = "Consistent video performance"
        elif trend_ratio > 0.5:
            score = 0.3
            factor = "Recent videos underperforming"
        else:
            score = 0.15
            factor = "Declining video performance"
        
        return score, factor


from typing import Any, Dict, List
from datetime import datetime, timedelta
from statistics import median, stdev
from app.metrics.base import BaseMetric, MetricResult


class CredibilityMetric(BaseMetric):
    """
    Credibility Module
    
    Signals:
    - Channel age (older = more established)
    - Median video length (longer = more in-depth content)
    - Upload consistency (regular uploads = committed creator)
    - External links (GitHub, papers = technical credibility)
    """
    
    name = "credibility"
    description = "Measures creator credibility based on channel age, content depth, and external validation"
    
    # Credibility-boosting domains
    CREDIBILITY_DOMAINS = [
        "github.com",
        "gitlab.com",
        "arxiv.org",
        "scholar.google",
        "researchgate.net",
        "linkedin.com",
        "twitter.com",
        "x.com",
        "medium.com",
        "substack.com",
        "dev.to",
        "stackoverflow.com",
        "huggingface.co",
        "kaggle.com",
    ]
    
    def available(self, creator_data: Dict[str, Any]) -> bool:
        """Credibility can always be computed if we have basic channel data"""
        return (
            creator_data.get("channel_created_date") is not None
            and len(creator_data.get("videos", [])) > 0
        )
    
    async def compute(self, creator_data: Dict[str, Any], **kwargs) -> MetricResult:
        if not self.available(creator_data):
            return MetricResult(
                score=0.0,
                available=False,
                factors=["Insufficient data for credibility calculation"]
            )
        
        factors = []
        scores = []
        
        # 1. Channel Age Score (0-1)
        channel_age_score, age_factor = self._compute_channel_age(creator_data)
        scores.append(channel_age_score * 0.25)
        factors.append(age_factor)
        
        # 2. Median Video Length Score (0-1)
        length_score, length_factor = self._compute_video_length(creator_data)
        scores.append(length_score * 0.25)
        factors.append(length_factor)
        
        # 3. Upload Consistency Score (0-1)
        consistency_score, consistency_factor = self._compute_upload_consistency(creator_data)
        scores.append(consistency_score * 0.25)
        factors.append(consistency_factor)
        
        # 4. External Links Score (0-1)
        links_score, links_factor = self._compute_external_links(creator_data)
        scores.append(links_score * 0.25)
        factors.append(links_factor)
        
        total_score = sum(scores)
        
        return MetricResult(
            score=total_score,
            available=True,
            factors=factors,
            raw_data={
                "channel_age_score": channel_age_score,
                "video_length_score": length_score,
                "consistency_score": consistency_score,
                "links_score": links_score,
            }
        )
    
    def _compute_channel_age(self, creator_data: Dict[str, Any]) -> tuple[float, str]:
        """Score based on channel age. 3+ years = max score"""
        created_date = creator_data.get("channel_created_date")
        if not created_date:
            return 0.0, "Channel creation date unknown"
        
        if isinstance(created_date, str):
            created_date = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
        
        age_days = (datetime.utcnow() - created_date.replace(tzinfo=None)).days
        age_years = age_days / 365
        
        # Score: 0 at 0 years, 1.0 at 3+ years
        score = min(1.0, age_years / 3.0)
        
        if age_years >= 3:
            factor = f"Established channel ({age_years:.1f} years)"
        elif age_years >= 1:
            factor = f"Developing channel ({age_years:.1f} years)"
        else:
            factor = f"Newer channel ({age_days} days)"
        
        return score, factor
    
    def _compute_video_length(self, creator_data: Dict[str, Any]) -> tuple[float, str]:
        """Score based on median video length. 10+ min = good depth"""
        videos = creator_data.get("videos", [])
        if not videos:
            return 0.0, "No videos available"
        
        durations = [v.get("duration_seconds", 0) for v in videos if v.get("duration_seconds", 0) > 60]
        if not durations:
            return 0.0, "No substantial videos found"
        
        median_duration = median(durations)
        median_minutes = median_duration / 60
        
        # Score: 0 at 0 min, 1.0 at 15+ min
        score = min(1.0, median_minutes / 15.0)
        
        if median_minutes >= 15:
            factor = f"In-depth content (median {median_minutes:.0f} min)"
        elif median_minutes >= 8:
            factor = f"Moderate depth (median {median_minutes:.0f} min)"
        else:
            factor = f"Shorter content (median {median_minutes:.0f} min)"
        
        return score, factor
    
    def _compute_upload_consistency(self, creator_data: Dict[str, Any]) -> tuple[float, str]:
        """Score based on upload regularity over the past year"""
        videos = creator_data.get("videos", [])
        if len(videos) < 3:
            return 0.3, "Too few videos to assess consistency"
        
        # Get videos from last year
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        recent_videos = []
        
        for v in videos:
            pub_date = v.get("published_at")
            if pub_date:
                if isinstance(pub_date, str):
                    pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                if pub_date.replace(tzinfo=None) > one_year_ago:
                    recent_videos.append(pub_date)
        
        if len(recent_videos) < 2:
            return 0.2, "Infrequent uploads in the past year"
        
        # Calculate gaps between uploads
        sorted_dates = sorted(recent_videos)
        gaps = []
        for i in range(1, len(sorted_dates)):
            gap = (sorted_dates[i].replace(tzinfo=None) - sorted_dates[i-1].replace(tzinfo=None)).days
            gaps.append(gap)
        
        avg_gap = sum(gaps) / len(gaps)
        
        # Score based on upload frequency
        # Weekly uploads (7 days) = 1.0, Monthly (30 days) = 0.5, Quarterly (90 days) = 0.2
        if avg_gap <= 7:
            score = 1.0
            factor = f"Very consistent (avg {avg_gap:.0f} days between uploads)"
        elif avg_gap <= 14:
            score = 0.85
            factor = f"Consistent bi-weekly uploads"
        elif avg_gap <= 30:
            score = 0.6
            factor = f"Monthly upload schedule"
        elif avg_gap <= 60:
            score = 0.4
            factor = f"Bi-monthly uploads"
        else:
            score = 0.2
            factor = f"Infrequent uploads (avg {avg_gap:.0f} days apart)"
        
        return score, factor
    
    def _compute_external_links(self, creator_data: Dict[str, Any]) -> tuple[float, str]:
        """Score based on quality of external links"""
        links = creator_data.get("external_links", [])
        if not links:
            return 0.3, "No external links found"
        
        credible_links = []
        for link in links:
            link_lower = link.lower()
            for domain in self.CREDIBILITY_DOMAINS:
                if domain in link_lower:
                    credible_links.append(domain)
                    break
        
        unique_domains = set(credible_links)
        
        # High value: GitHub, arXiv, LinkedIn
        high_value = {"github.com", "gitlab.com", "arxiv.org", "huggingface.co", "kaggle.com"}
        high_value_count = len(unique_domains & high_value)
        
        # Score based on link quality
        base_score = min(0.5, len(unique_domains) * 0.15)
        bonus_score = min(0.5, high_value_count * 0.2)
        score = base_score + bonus_score
        
        if high_value_count > 0:
            factor = f"Strong external presence ({', '.join(unique_domains & high_value)})"
        elif len(unique_domains) > 0:
            factor = f"Active online presence ({len(unique_domains)} platforms)"
        else:
            factor = "Limited external validation"
        
        return min(1.0, score), factor


from typing import Any, Dict, List, Optional
import numpy as np
from app.metrics.base import BaseMetric, MetricResult


# Cache for creator content embeddings (simple in-memory)
_content_embedding_cache: Dict[str, List[float]] = {}


class TopicAuthorityMetric(BaseMetric):
    """
    Topic Authority Module
    
    Measures how well a creator's content aligns with target expertise topics.
    
    Steps:
    1. Embed transcripts (if available) or titles/descriptions
    2. Compute cosine similarity with topic query embedding
    3. Measure topic concentration (how focused vs scattered)
    
    Output:
    - topic_score ∈ [0,1]
    - topic_purity (concentration measure)
    """
    
    name = "topic_authority"
    description = "Measures alignment between creator content and target expertise topics"
    
    def available(self, creator_data: Dict[str, Any]) -> bool:
        """Need at least video titles/descriptions to compute topic authority"""
        videos = creator_data.get("videos", [])
        return len(videos) > 0
    
    async def compute(
        self,
        creator_data: Dict[str, Any],
        topic_embedding: Optional[List[float]] = None,
        topic_keywords: Optional[List[str]] = None,
        embedding_service = None,
        **kwargs
    ) -> MetricResult:
        if not self.available(creator_data):
            return MetricResult(
                score=0.0,
                available=False,
                factors=["No video content available for topic analysis"]
            )
        
        if topic_embedding is None and not topic_keywords:
            return MetricResult(
                score=0.5,
                available=True,
                factors=["No topic query provided - using neutral score"]
            )
        
        factors = []
        videos = creator_data.get("videos", [])
        
        # Get or generate content embedding for this creator
        content_embedding = await self._get_or_create_content_embedding(
            creator_data, embedding_service
        )
        
        if topic_embedding is not None and content_embedding is not None:
            # Compute similarity between topic and creator's content
            topic_vec = np.array(topic_embedding)
            content_vec = np.array(content_embedding)
            
            similarity = self._cosine_similarity(topic_vec, content_vec)
            
            # Cosine similarity ranges from -1 to 1, normalize to 0-1
            # Typically values are 0.1-0.5 for somewhat related, 0.5+ for very related
            # Scale to make it more meaningful
            score = min(1.0, max(0.0, (similarity + 0.2) * 1.25))
            
            # Determine strength description
            if similarity >= 0.5:
                strength = "Strong"
            elif similarity >= 0.35:
                strength = "Good"
            elif similarity >= 0.2:
                strength = "Moderate"
            else:
                strength = "Weak"
            
            factors.append(f"{strength} semantic match (similarity: {similarity:.2f})")
            factors.append(f"Analyzed {len(videos)} videos")
            
            return MetricResult(
                score=score,
                available=True,
                factors=factors,
                raw_data={
                    "similarity": similarity,
                    "videos_analyzed": len(videos)
                }
            )
        
        # Fallback: keyword matching if no embeddings
        if topic_keywords:
            keyword_score, keyword_factors = self._keyword_matching(videos, topic_keywords)
            return MetricResult(
                score=keyword_score,
                available=True,
                factors=keyword_factors,
                raw_data={"method": "keyword_matching"}
            )
        
        return MetricResult(
            score=0.5,
            available=True,
            factors=["Unable to compute topic match - insufficient data"]
        )
    
    async def _get_or_create_content_embedding(
        self, 
        creator_data: Dict[str, Any],
        embedding_service
    ) -> Optional[List[float]]:
        """Get or create a combined content embedding for creator"""
        channel_id = creator_data.get("channel_id", "")
        
        # Check cache first
        if channel_id in _content_embedding_cache:
            return _content_embedding_cache[channel_id]
        
        # If no embedding service, can't create embeddings
        if embedding_service is None:
            return None
        
        # Build content text from videos
        videos = creator_data.get("videos", [])
        if not videos:
            return None
        
        # Combine channel description + video titles + descriptions
        content_parts = []
        
        # Channel description
        channel_desc = creator_data.get("channel_description", "")
        if channel_desc:
            content_parts.append(f"Channel: {channel_desc[:500]}")
        
        # Video titles and descriptions (top 15 most viewed)
        sorted_videos = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)[:15]
        for video in sorted_videos:
            title = video.get("title", "")
            desc = video.get("description", "")[:200]  # First 200 chars
            tags = ", ".join(video.get("tags", [])[:5])
            
            video_text = f"Video: {title}"
            if desc:
                video_text += f". {desc}"
            if tags:
                video_text += f". Tags: {tags}"
            content_parts.append(video_text)
        
        # Combine all content
        combined_text = "\n".join(content_parts)
        
        if not combined_text.strip():
            return None
        
        try:
            embedding = await embedding_service.embed_text(combined_text)
            # Cache it
            _content_embedding_cache[channel_id] = embedding
            return embedding
        except Exception as e:
            print(f"Error creating content embedding: {e}")
            return None
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def _keyword_matching(
        self,
        videos: List[Dict[str, Any]],
        keywords: List[str]
    ) -> tuple[float, List[str]]:
        """Fallback keyword matching when embeddings aren't available"""
        if not keywords or not videos:
            return 0.0, ["No keywords or videos for matching"]
        
        keywords_lower = [k.lower() for k in keywords]
        total_matches = 0
        videos_with_matches = 0
        keyword_counts = {k: 0 for k in keywords_lower}
        
        for video in videos:
            title = video.get("title", "").lower()
            description = video.get("description", "").lower()
            tags = " ".join(video.get("tags", [])).lower()
            content = f"{title} {description} {tags}"
            
            video_matches = 0
            for keyword in keywords_lower:
                count = content.count(keyword)
                if count > 0:
                    keyword_counts[keyword] += 1
                    video_matches += count
            
            if video_matches > 0:
                videos_with_matches += 1
            total_matches += video_matches
        
        # Calculate score
        coverage = videos_with_matches / len(videos) if videos else 0
        keyword_coverage = sum(1 for c in keyword_counts.values() if c > 0) / len(keywords_lower)
        
        score = (coverage * 0.6 + keyword_coverage * 0.4)
        
        factors = [
            f"{videos_with_matches}/{len(videos)} videos contain target keywords",
            f"{sum(1 for c in keyword_counts.values() if c > 0)}/{len(keywords)} keywords found"
        ]
        
        # Add most common keywords
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_keywords and top_keywords[0][1] > 0:
            factors.append(f"Top matches: {', '.join(k for k, v in top_keywords if v > 0)}")
        
        return score, factors


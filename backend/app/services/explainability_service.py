from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from openai import OpenAI
from app.core.config import get_settings
from app.services.scoring_engine import ScoringResult

settings = get_settings()


class ExplainabilityService:
    """
    Generates human-readable explanations for why a creator is recommended.
    
    Output:
    - Per-metric explanations with actual data
    - Links to relevant videos/repos
    - Suggested call topics
    """
    
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def generate_why_expert(
        self,
        creator_data: Dict[str, Any],
        scoring_result: ScoringResult,
        topic_query: str,
    ) -> Dict[str, Any]:
        """
        Generate the "Why This Expert" explanation.
        
        Returns:
            {
                "bullets": ["reason 1", "reason 2", ...],
                "relevant_content": [{"title": "", "url": "", "relevance": ""}],
                "suggested_topics": ["topic 1", "topic 2", ...]
            }
        """
        # Generate bullets from scoring factors + LLM enhancement
        bullets = self._generate_rationale_bullets(creator_data, scoring_result, topic_query)
        
        # Find relevant content
        relevant_content = self._find_relevant_content(creator_data, topic_query)
        
        # Generate suggested call topics
        suggested_topics = await self._generate_suggested_topics(creator_data, topic_query)
        
        return {
            "bullets": bullets,
            "relevant_content": relevant_content,
            "suggested_topics": suggested_topics,
        }
    
    def _generate_rationale_bullets(
        self,
        creator_data: Dict[str, Any],
        scoring_result: ScoringResult,
        topic_query: str,
    ) -> List[str]:
        """Generate detailed per-metric explanations with actual numbers"""
        bullets = []
        subscores = scoring_result.metric_scores
        
        # Always start with subscriber count
        subs = creator_data.get("total_subscribers", 0)
        views = creator_data.get("total_views", 0)
        bullets.append(f"Audience: {format_subscriber_count(subs)} subscribers, {format_view_count(views)} total views")
        
        # Topic Authority / Content Match
        if "topic_authority" in subscores and subscores["topic_authority"].available:
            topic = subscores["topic_authority"]
            score_pct = int(topic.score * 100)
            if topic.score >= 0.7:
                bullets.append(f"Topic Match ({score_pct}%): Strong alignment with '{topic_query}'. Multiple videos directly cover this subject.")
            elif topic.score >= 0.4:
                bullets.append(f"Topic Match ({score_pct}%): Moderate alignment with '{topic_query}'. Some relevant content found.")
            else:
                bullets.append(f"Topic Match ({score_pct}%): Limited coverage of '{topic_query}'. Content touches related areas.")
        
        # Credibility
        if "credibility" in subscores and subscores["credibility"].available:
            cred = subscores["credibility"]
            score_pct = int(cred.score * 100)
            
            # Build credibility reasons
            reasons = []
            channel_age = creator_data.get("channel_created_date")
            if channel_age:
                try:
                    if isinstance(channel_age, str):
                        created = datetime.fromisoformat(channel_age.replace('Z', '+00:00'))
                    else:
                        created = channel_age
                    years = (datetime.now(created.tzinfo) - created).days // 365
                    if years >= 5:
                        reasons.append(f"{years}+ years on platform")
                    elif years >= 2:
                        reasons.append(f"{years} years experience")
                except:
                    pass
            
            links = creator_data.get("external_links", [])
            if any("github.com" in l.lower() for l in links):
                reasons.append("has GitHub")
            if any("linkedin.com" in l.lower() for l in links):
                reasons.append("verified LinkedIn")
            
            if cred.score >= 0.7:
                reason_str = f" — {', '.join(reasons)}." if reasons else "."
                bullets.append(f"Credibility ({score_pct}%): Established creator{reason_str}")
            elif cred.score >= 0.4:
                bullets.append(f"Credibility ({score_pct}%): Building reputation with consistent content quality.")
            else:
                bullets.append(f"Credibility ({score_pct}%): Newer creator, still establishing track record.")
        
        # Freshness - with actual recent post date
        if "freshness" in subscores and subscores["freshness"].available:
            fresh = subscores["freshness"]
            score_pct = int(fresh.score * 100)
            
            # Find most recent video
            videos = creator_data.get("videos", [])
            recent_date = None
            if videos:
                for v in videos:
                    pub_date = v.get("published_at")
                    if pub_date:
                        try:
                            if isinstance(pub_date, str):
                                d = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                            else:
                                d = pub_date
                            if recent_date is None or d > recent_date:
                                recent_date = d
                        except:
                            pass
            
            if recent_date:
                days_ago = (datetime.now(recent_date.tzinfo) - recent_date).days
                if days_ago == 0:
                    time_str = "today"
                elif days_ago == 1:
                    time_str = "yesterday"
                elif days_ago < 7:
                    time_str = f"{days_ago} days ago"
                elif days_ago < 30:
                    weeks = days_ago // 7
                    time_str = f"{weeks} week{'s' if weeks > 1 else ''} ago"
                elif days_ago < 365:
                    months = days_ago // 30
                    time_str = f"{months} month{'s' if months > 1 else ''} ago"
                else:
                    years = days_ago // 365
                    time_str = f"{years} year{'s' if years > 1 else ''} ago"
                
                if fresh.score >= 0.7:
                    bullets.append(f"Freshness ({score_pct}%): Very active. Last upload {time_str}.")
                elif fresh.score >= 0.4:
                    bullets.append(f"Freshness ({score_pct}%): Moderately active. Last upload {time_str}.")
                else:
                    bullets.append(f"Freshness ({score_pct}%): Infrequent uploads. Last post {time_str}.")
            else:
                bullets.append(f"Freshness ({score_pct}%): Activity data unavailable.")
        
        # Growth - with actual rate
        if "growth" in subscores and subscores["growth"].available:
            growth = subscores["growth"]
            score_pct = int(growth.score * 100)
            
            rate = None
            if growth.raw_data and "growth_rate" in growth.raw_data:
                rate = growth.raw_data["growth_rate"]
            
            if rate is not None:
                if rate > 0:
                    if growth.score >= 0.7:
                        bullets.append(f"Growth ({score_pct}%): Strong trajectory with +{rate:.1f}% subscriber increase.")
                    elif growth.score >= 0.4:
                        bullets.append(f"Growth ({score_pct}%): Steady at +{rate:.1f}% subscriber increase.")
                    else:
                        bullets.append(f"Growth ({score_pct}%): Slow growth at +{rate:.1f}%.")
                elif rate < 0:
                    bullets.append(f"Growth ({score_pct}%): Declining, {rate:.1f}% subscriber loss.")
                else:
                    bullets.append(f"Growth ({score_pct}%): Stable audience, no significant change.")
            else:
                if growth.score >= 0.7:
                    bullets.append(f"Growth ({score_pct}%): Strong growth trajectory.")
                elif growth.score >= 0.4:
                    bullets.append(f"Growth ({score_pct}%): Moderate audience growth.")
                else:
                    bullets.append(f"Growth ({score_pct}%): Limited recent growth.")
        
        # Communication (if available)
        if "communication" in subscores and subscores["communication"].available:
            comm = subscores["communication"]
            if comm.score > 0:
                score_pct = int(comm.score * 100)
                if comm.score >= 0.7:
                    bullets.append(f"Communication ({score_pct}%): Clear, well-structured explanations.")
                elif comm.score >= 0.4:
                    bullets.append(f"Communication ({score_pct}%): Good presentation style.")
                else:
                    bullets.append(f"Communication ({score_pct}%): Quality varies across content.")
        
        return bullets
    
    def _find_relevant_content(
        self,
        creator_data: Dict[str, Any],
        topic_query: str,
    ) -> List[Dict[str, str]]:
        """Find most relevant videos/content"""
        videos = creator_data.get("videos", [])
        query_lower = topic_query.lower()
        query_terms = query_lower.split()
        
        # Score videos by relevance
        scored_videos = []
        for video in videos:
            title = video.get("title", "").lower()
            desc = video.get("description", "").lower()
            tags = " ".join(video.get("tags", [])).lower()
            
            score = 0
            for term in query_terms:
                if term in title:
                    score += 3
                if term in desc:
                    score += 1
                if term in tags:
                    score += 2
            
            # Boost recent videos
            views = video.get("views", 0)
            score += min(2, views / 100000)  # Small boost for popular videos
            
            if score > 0:
                scored_videos.append((score, video))
        
        # Sort by score and take top 3
        scored_videos.sort(key=lambda x: x[0], reverse=True)
        
        relevant = []
        for score, video in scored_videos[:3]:
            video_id = video.get("video_id")
            relevant.append({
                "title": video.get("title"),
                "url": f"https://youtube.com/watch?v={video_id}",
                "relevance": self._describe_relevance(video, topic_query),
                "views": video.get("views", 0),
            })
        
        # Add external links
        links = creator_data.get("external_links", [])
        for link in links[:2]:
            if "github.com" in link:
                relevant.append({
                    "title": "GitHub Profile",
                    "url": link,
                    "relevance": "Open source work and code examples",
                })
            elif "huggingface.co" in link:
                relevant.append({
                    "title": "Hugging Face",
                    "url": link,
                    "relevance": "ML models and datasets",
                })
        
        return relevant[:5]
    
    def _describe_relevance(self, video: Dict[str, Any], topic: str) -> str:
        """Generate a brief relevance description"""
        title = video.get("title", "")
        views = video.get("views", 0)
        
        if views >= 100000:
            return f"Popular video on related topic ({views:,} views)"
        elif views >= 10000:
            return f"Well-received content ({views:,} views)"
        else:
            return "Relevant to your search topic"
    
    async def _generate_suggested_topics(
        self,
        creator_data: Dict[str, Any],
        topic_query: str,
    ) -> List[str]:
        """Generate suggested call/consultation topics"""
        if not self.client:
            return self._fallback_topics(creator_data, topic_query)
        
        # Use LLM to generate suggested topics
        channel_name = creator_data.get("channel_name", "Creator")
        recent_videos = creator_data.get("videos", [])[:5]
        video_titles = [v.get("title", "") for v in recent_videos]
        
        prompt = f"""Based on this YouTube creator's content, suggest 3-4 specific topics 
for an expert consultation call. The search topic was: "{topic_query}"

Creator: {channel_name}
Recent video titles:
{chr(10).join(f'- {t}' for t in video_titles)}

Generate 3-4 specific, actionable consultation topics. Be concise (under 10 words each).
Output as a simple list, one topic per line, no bullets or numbers."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7,
            )
            
            topics = response.choices[0].message.content.strip().split("\n")
            return [t.strip().lstrip("•-123456789. ") for t in topics if t.strip()][:4]
        except Exception:
            return self._fallback_topics(creator_data, topic_query)
    
    def _fallback_topics(
        self,
        creator_data: Dict[str, Any],
        topic_query: str,
    ) -> List[str]:
        """Generate topics without LLM"""
        topics = [
            f"Deep dive into {topic_query}",
            "Industry trends and predictions",
            "Best practices and common pitfalls",
        ]
        
        # Add based on content
        videos = creator_data.get("videos", [])
        if videos:
            # Extract common terms from titles
            title_words = []
            for v in videos[:10]:
                title_words.extend(v.get("title", "").split())
            
            # Find technical terms (capitalized, long words)
            tech_terms = [w for w in title_words if len(w) > 5 and w[0].isupper()]
            if tech_terms:
                topics.append(f"Technical discussion on {tech_terms[0]}")
        
        return topics[:4]


def format_subscriber_count(count: int) -> str:
    """Format subscriber count for display"""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


def format_view_count(count: int) -> str:
    """Format view count for display"""
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    elif count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.0f}K"
    else:
        return str(count)


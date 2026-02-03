from typing import List, Dict, Any, Optional
from datetime import datetime
import isodate
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import get_settings

settings = get_settings()


class YouTubeService:
    """Service for interacting with YouTube Data API"""
    
    def __init__(self):
        self.youtube = None
        if settings.YOUTUBE_API_KEY:
            self.youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
    
    def _ensure_client(self):
        if not self.youtube:
            raise ValueError("YouTube API key not configured")
    
    async def search_channels(
        self,
        query: str,
        max_results: int = 50,
        relevance_language: str = "en"
    ) -> List[Dict[str, Any]]:
        """Search for YouTube channels by query"""
        self._ensure_client()
        
        try:
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="channel",
                maxResults=min(max_results, 50),
                relevanceLanguage=relevance_language,
            )
            response = request.execute()
            
            channels = []
            for item in response.get("items", []):
                channels.append({
                    "channel_id": item["snippet"]["channelId"],
                    "channel_name": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "thumbnail_url": item["snippet"]["thumbnails"].get("high", {}).get("url"),
                })
            
            return channels
        except HttpError as e:
            raise Exception(f"YouTube API error: {e}")
    
    async def get_channel_details(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed channel information"""
        self._ensure_client()
        
        try:
            request = self.youtube.channels().list(
                part="snippet,statistics,brandingSettings,topicDetails",
                id=channel_id
            )
            response = request.execute()
            
            if not response.get("items"):
                return None
            
            item = response["items"][0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            branding = item.get("brandingSettings", {}).get("channel", {})
            
            # Extract external links from description
            description = snippet.get("description", "")
            external_links = self._extract_links(description)
            
            # Add custom URL if available
            if branding.get("customUrl"):
                external_links.append(f"https://youtube.com/{branding['customUrl']}")
            
            return {
                "channel_id": channel_id,
                "channel_name": snippet.get("title"),
                "channel_description": description,
                "total_subscribers": int(stats.get("subscriberCount", 0)),
                "total_views": int(stats.get("viewCount", 0)),
                "total_videos": int(stats.get("videoCount", 0)),
                "channel_created_date": snippet.get("publishedAt"),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "country": snippet.get("country"),
                "external_links": external_links,
                "keywords": branding.get("keywords", "").split(),
                "topic_categories": item.get("topicDetails", {}).get("topicCategories", []),
            }
        except HttpError as e:
            raise Exception(f"YouTube API error: {e}")
    
    async def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent videos from a channel"""
        self._ensure_client()
        
        try:
            # First get upload playlist ID
            request = self.youtube.channels().list(
                part="contentDetails",
                id=channel_id
            )
            response = request.execute()
            
            if not response.get("items"):
                return []
            
            uploads_playlist = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get videos from playlist
            videos = []
            next_page_token = None
            
            while len(videos) < max_results:
                request = self.youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist,
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                )
                response = request.execute()
                
                video_ids = [item["contentDetails"]["videoId"] for item in response.get("items", [])]
                
                if video_ids:
                    video_details = await self._get_video_details(video_ids)
                    videos.extend(video_details)
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break
            
            return videos[:max_results]
        except HttpError as e:
            raise Exception(f"YouTube API error: {e}")
    
    async def _get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Get detailed video information"""
        try:
            request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            )
            response = request.execute()
            
            videos = []
            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                content = item.get("contentDetails", {})
                
                # Parse duration
                duration_str = content.get("duration", "PT0S")
                try:
                    duration = isodate.parse_duration(duration_str)
                    duration_seconds = int(duration.total_seconds())
                except:
                    duration_seconds = 0
                
                # Check for captions
                has_captions = content.get("caption", "false") == "true"
                
                videos.append({
                    "video_id": item["id"],
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "published_at": snippet.get("publishedAt"),
                    "duration_seconds": duration_seconds,
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "has_captions": has_captions,
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    "tags": snippet.get("tags", []),
                })
            
            return videos
        except HttpError as e:
            raise Exception(f"YouTube API error: {e}")
    
    def _extract_links(self, text: str) -> List[str]:
        """Extract URLs from text"""
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        # Filter for relevant domains
        relevant_domains = [
            "github.com", "gitlab.com", "twitter.com", "x.com",
            "linkedin.com", "medium.com", "substack.com", "dev.to",
            "arxiv.org", "huggingface.co", "kaggle.com"
        ]
        
        filtered = []
        for url in urls:
            url_lower = url.lower()
            if any(domain in url_lower for domain in relevant_domains):
                filtered.append(url)
            elif not any(d in url_lower for d in ["youtube.com", "youtu.be"]):
                # Include other non-YouTube links too
                filtered.append(url)
        
        return list(set(filtered))[:10]  # Limit to 10 unique links


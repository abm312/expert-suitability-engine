from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urlparse

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)


class YouTubeCatalogService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = build("youtube", "v3", developerKey=api_key) if api_key else None

    def ensure_client(self) -> None:
        if not self.client:
            raise ValueError("YOUTUBE_API_KEY is not configured")

    def resolve_channel(
        self,
        *,
        channel_id: str | None = None,
        channel_url: str | None = None,
        channel_handle: str | None = None,
        search_query: str | None = None,
    ) -> dict[str, str]:
        self.ensure_client()
        logger.info(
            "Resolving channel source channel_id=%s channel_url=%s channel_handle=%s search_query=%s",
            channel_id,
            channel_url,
            channel_handle,
            search_query,
        )

        if channel_id:
            logger.info("Resolving channel directly via channel_id=%s", channel_id)
            return self.get_channel_metadata(channel_id)

        if channel_url:
            parsed_channel_id = self._extract_channel_id_from_url(channel_url)
            if parsed_channel_id:
                logger.info(
                    "Resolved channel URL to explicit channel_id=%s",
                    parsed_channel_id,
                )
                channel = self.get_channel_metadata(parsed_channel_id)
                channel["source_url"] = channel_url
                return channel

            guessed_query = self._extract_query_from_url(channel_url)
            if guessed_query:
                logger.info(
                    "Resolved channel URL to search query=%s",
                    guessed_query,
                )
                channel = self.search_channel(guessed_query)
                channel["source_url"] = channel_url
                return channel

        if channel_handle:
            normalized = channel_handle.lstrip("@")
            logger.info("Resolving channel via handle=%s", normalized)
            return self.search_channel(normalized)

        if search_query:
            logger.info("Resolving channel via search_query=%s", search_query)
            return self.search_channel(search_query)

        raise ValueError("A channel source is required")

    def search_channel(self, query: str) -> dict[str, str]:
        self.ensure_client()
        logger.info("Searching YouTube channel for query=%s", query)
        try:
            response = (
                self.client.search()
                .list(
                    part="snippet",
                    q=query,
                    type="channel",
                    maxResults=1,
                )
                .execute()
            )
        except HttpError as exc:
            raise RuntimeError(f"YouTube search failed: {exc}") from exc

        items = response.get("items", [])
        if not items:
            raise ValueError(f"No channel found for query '{query}'")

        item = items[0]
        channel_id = item["snippet"]["channelId"]
        logger.info("YouTube channel search matched channel_id=%s for query=%s", channel_id, query)
        metadata = self.get_channel_metadata(channel_id)
        metadata.setdefault("source_url", f"https://youtube.com/channel/{channel_id}")
        return metadata

    def get_channel_metadata(self, channel_id: str) -> dict[str, str]:
        self.ensure_client()
        logger.info("Loading channel metadata channel_id=%s", channel_id)
        try:
            response = (
                self.client.channels()
                .list(part="snippet,contentDetails", id=channel_id)
                .execute()
            )
        except HttpError as exc:
            raise RuntimeError(f"Unable to load channel metadata: {exc}") from exc

        items = response.get("items", [])
        if not items:
            raise ValueError(f"Channel '{channel_id}' was not found")

        item = items[0]
        snippet = item.get("snippet", {})
        uploads = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        if not uploads:
            raise ValueError(f"Channel '{channel_id}' has no uploads playlist")

        logger.info(
            "Loaded channel metadata channel_id=%s channel_name=%s uploads_playlist_id=%s",
            channel_id,
            snippet.get("title") or channel_id,
            uploads,
        )

        return {
            "channel_id": channel_id,
            "channel_name": snippet.get("title") or channel_id,
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "uploads_playlist_id": uploads,
            "source_url": f"https://youtube.com/channel/{channel_id}",
            "synced_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }

    def get_recent_videos(self, channel_id: str, max_videos: int) -> list[dict[str, str]]:
        logger.info(
            "Loading recent videos channel_id=%s max_videos=%s",
            channel_id,
            max_videos,
        )
        channel = self.get_channel_metadata(channel_id)
        uploads_playlist_id = channel["uploads_playlist_id"]

        videos: list[dict[str, str]] = []
        next_page_token = None

        while len(videos) < max_videos:
            try:
                response = (
                    self.client.playlistItems()
                    .list(
                        part="contentDetails",
                        playlistId=uploads_playlist_id,
                        maxResults=min(50, max_videos - len(videos)),
                        pageToken=next_page_token,
                    )
                    .execute()
                )
            except HttpError as exc:
                raise RuntimeError(f"Unable to list channel videos: {exc}") from exc

            items = response.get("items", [])
            video_ids = [item["contentDetails"]["videoId"] for item in items]
            if video_ids:
                logger.info(
                    "Playlist page returned %s video ids for channel_id=%s",
                    len(video_ids),
                    channel_id,
                )
                videos.extend(self._get_video_details(video_ids))

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        final_videos = videos[:max_videos]
        logger.info(
            "Loaded recent videos channel_id=%s final_count=%s",
            channel_id,
            len(final_videos),
        )
        return final_videos

    def _get_video_details(self, video_ids: list[str]) -> list[dict[str, str]]:
        logger.info("Loading video details for %s video ids", len(video_ids))
        try:
            response = (
                self.client.videos()
                .list(
                    part="snippet,contentDetails",
                    id=",".join(video_ids),
                )
                .execute()
            )
        except HttpError as exc:
            raise RuntimeError(f"Unable to load video details: {exc}") from exc

        videos: list[dict[str, str]] = []
        timestamp = datetime.utcnow().isoformat()
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            videos.append(
                {
                    "video_id": item["id"],
                    "title": snippet.get("title") or item["id"],
                    "published_at": snippet.get("publishedAt"),
                    "caption_hint": content.get("caption", "false") == "true",
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    "updated_at": timestamp,
                    "created_at": timestamp,
                }
            )
        logger.info("Loaded video details count=%s", len(videos))
        return videos

    @staticmethod
    def _extract_channel_id_from_url(channel_url: str) -> str | None:
        parsed = urlparse(channel_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] == "channel" and path_parts[1].startswith("UC"):
            return path_parts[1]
        return None

    @staticmethod
    def _extract_query_from_url(channel_url: str) -> str | None:
        parsed = urlparse(channel_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if not path_parts:
            return None
        if path_parts[0].startswith("@"):
            return path_parts[0].lstrip("@")
        if path_parts[0] in {"user", "c"} and len(path_parts) > 1:
            return path_parts[1]
        return None

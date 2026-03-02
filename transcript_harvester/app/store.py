import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional


class SQLiteStore:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id TEXT PRIMARY KEY,
                    channel_name TEXT NOT NULL,
                    source_url TEXT,
                    thumbnail_url TEXT,
                    synced_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    published_at TEXT,
                    caption_hint INTEGER NOT NULL DEFAULT 0,
                    thumbnail_url TEXT,
                    transcript_status TEXT NOT NULL DEFAULT 'pending',
                    transcript_error TEXT,
                    last_transcript_attempt_at TEXT,
                    updated_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS transcripts (
                    video_id TEXT PRIMARY KEY,
                    language TEXT,
                    is_generated INTEGER,
                    segment_count INTEGER NOT NULL DEFAULT 0,
                    text TEXT NOT NULL,
                    segments_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    FOREIGN KEY(video_id) REFERENCES videos(video_id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at)"
            )

    def upsert_channel(self, channel: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO channels (
                    channel_id, channel_name, source_url, thumbnail_url, synced_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    channel_name = excluded.channel_name,
                    source_url = excluded.source_url,
                    thumbnail_url = excluded.thumbnail_url,
                    synced_at = excluded.synced_at
                """,
                (
                    channel["channel_id"],
                    channel["channel_name"],
                    channel.get("source_url"),
                    channel.get("thumbnail_url"),
                    channel["synced_at"],
                    channel["created_at"],
                ),
            )

    def upsert_videos(self, channel_id: str, videos: list[dict[str, Any]]) -> None:
        with self.connect() as connection:
            for video in videos:
                connection.execute(
                    """
                    INSERT INTO videos (
                        video_id, channel_id, title, published_at, caption_hint, thumbnail_url,
                        updated_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(video_id) DO UPDATE SET
                        channel_id = excluded.channel_id,
                        title = excluded.title,
                        published_at = excluded.published_at,
                        caption_hint = excluded.caption_hint,
                        thumbnail_url = excluded.thumbnail_url,
                        updated_at = excluded.updated_at
                    """,
                    (
                        video["video_id"],
                        channel_id,
                        video["title"],
                        video.get("published_at"),
                        1 if video.get("caption_hint") else 0,
                        video.get("thumbnail_url"),
                        video["updated_at"],
                        video["created_at"],
                    ),
                )

    def get_cached_transcript(self, video_id: str) -> Optional[dict[str, Any]]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    v.video_id,
                    v.title,
                    v.published_at,
                    v.caption_hint,
                    v.transcript_status,
                    v.transcript_error,
                    t.language,
                    t.is_generated,
                    t.segment_count,
                    t.text,
                    t.segments_json
                FROM videos v
                LEFT JOIN transcripts t ON t.video_id = v.video_id
                WHERE v.video_id = ?
                """,
                (video_id,),
            ).fetchone()

        if not row or not row["text"]:
            return None

        return {
            "video_id": row["video_id"],
            "title": row["title"],
            "published_at": row["published_at"],
            "caption_hint": bool(row["caption_hint"]),
            "transcript_status": row["transcript_status"],
            "transcript_error": row["transcript_error"],
            "transcript_language": row["language"],
            "is_generated": self._coerce_bool(row["is_generated"]),
            "segment_count": row["segment_count"] or 0,
            "transcript_text": row["text"],
            "segments": json.loads(row["segments_json"]),
        }

    def save_transcript(self, video_id: str, transcript: dict[str, Any], attempted_at: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO transcripts (
                    video_id, language, is_generated, segment_count, text, segments_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    language = excluded.language,
                    is_generated = excluded.is_generated,
                    segment_count = excluded.segment_count,
                    text = excluded.text,
                    segments_json = excluded.segments_json,
                    fetched_at = excluded.fetched_at
                """,
                (
                    video_id,
                    transcript.get("language"),
                    self._bool_to_int(transcript.get("is_generated")),
                    transcript.get("segment_count", 0),
                    transcript["text"],
                    json.dumps(transcript.get("segments", [])),
                    transcript["fetched_at"],
                ),
            )
            connection.execute(
                """
                UPDATE videos
                SET transcript_status = 'fetched',
                    transcript_error = NULL,
                    last_transcript_attempt_at = ?
                WHERE video_id = ?
                """,
                (attempted_at, video_id),
            )

    def mark_transcript_failure(self, video_id: str, error: str, attempted_at: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE videos
                SET transcript_status = 'missing',
                    transcript_error = ?,
                    last_transcript_attempt_at = ?
                WHERE video_id = ?
                """,
                (error, attempted_at, video_id),
            )

    def get_channel_name(self, channel_id: str) -> Optional[str]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT channel_name FROM channels WHERE channel_id = ?",
                (channel_id,),
            ).fetchone()
        return row["channel_name"] if row else None

    def get_cached_channel_transcripts(
        self, channel_id: str, limit: int
    ) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    v.video_id,
                    v.title,
                    v.published_at,
                    v.caption_hint,
                    v.transcript_status,
                    v.transcript_error,
                    t.language,
                    t.is_generated,
                    t.segment_count,
                    t.text,
                    t.segments_json
                FROM videos v
                LEFT JOIN transcripts t ON t.video_id = v.video_id
                WHERE v.channel_id = ?
                ORDER BY COALESCE(v.published_at, '') DESC
                LIMIT ?
                """,
                (channel_id, limit),
            ).fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            items.append(
                {
                    "video_id": row["video_id"],
                    "title": row["title"],
                    "published_at": row["published_at"],
                    "caption_hint": bool(row["caption_hint"]),
                    "transcript_status": row["transcript_status"],
                    "transcript_error": row["transcript_error"],
                    "transcript_language": row["language"],
                    "is_generated": self._coerce_bool(row["is_generated"]),
                    "segment_count": row["segment_count"] or 0,
                    "transcript_text": row["text"],
                    "segments": json.loads(row["segments_json"]) if row["segments_json"] else [],
                }
            )
        return items

    @staticmethod
    def _bool_to_int(value: Optional[bool]) -> Optional[int]:
        if value is None:
            return None
        return 1 if value else 0

    @staticmethod
    def _coerce_bool(value: Optional[int]) -> Optional[bool]:
        if value is None:
            return None
        return bool(value)

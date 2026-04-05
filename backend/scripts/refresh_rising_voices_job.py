import asyncio
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.core.rising_voices import (
    RISING_VOICES_FILTERS,
    RISING_VOICES_METRICS,
    RISING_VOICES_QUERIES,
)
from app.db.database import AsyncSessionLocal
from app.services.creator_service import CreatorService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("rising_voices_job")


async def main() -> int:
    settings = get_settings()
    service = CreatorService()

    logger.info(
        "Starting daily Rising AI Voices refresh: final_limit=%s per_query_limit=%s min_topic_authority=%s",
        settings.RISING_VOICES_FINAL_LIMIT,
        settings.RISING_VOICES_PER_QUERY_LIMIT,
        settings.RISING_VOICES_MIN_TOPIC_AUTHORITY,
    )

    async with AsyncSessionLocal() as db:
        try:
            refresh_result = await service.refresh_rising_voices_snapshot(
                db=db,
                queries=RISING_VOICES_QUERIES,
                metrics=RISING_VOICES_METRICS,
                filters=RISING_VOICES_FILTERS,
                final_limit=settings.RISING_VOICES_FINAL_LIMIT,
                per_query_limit=settings.RISING_VOICES_PER_QUERY_LIMIT,
                min_topic_authority=settings.RISING_VOICES_MIN_TOPIC_AUTHORITY,
            )
            logger.info(
                "Rising AI Voices refresh complete: count=%s refreshed_at=%s",
                refresh_result["count"],
                refresh_result["refreshed_at"].isoformat(),
            )
            return 0
        except Exception:
            await db.rollback()
            logger.exception("Rising AI Voices refresh job failed")
            return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Transcript Harvester"
    APP_VERSION: str = "1.0.0"
    PORT: int = 8100

    YOUTUBE_API_KEY: str = ""

    DATA_DIR: str = "./data"
    OUTPUT_DIR: str = "./dumps"
    DATABASE_FILENAME: str = "transcript_harvester.db"

    DEFAULT_MAX_VIDEOS: int = 10
    DEFAULT_LANGUAGES: list[str] = ["en"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TH_",
        extra="ignore",
    )

    @property
    def database_path(self) -> Path:
        return Path(self.DATA_DIR) / self.DATABASE_FILENAME


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()

    # Allow plain YOUTUBE_API_KEY from the shell if TH_YOUTUBE_API_KEY is not set.
    if not settings.YOUTUBE_API_KEY:
        import os

        settings.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

    return settings

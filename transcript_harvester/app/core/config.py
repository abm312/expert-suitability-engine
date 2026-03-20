import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Transcript Scraper"
    APP_VERSION: str = "1.0.0"
    PORT: int = 8100

    YOUTUBE_API_KEY: str = ""
    TRANSCRIPT_PROVIDER: str = "auto"
    SUPADATA_API_KEY: str = ""
    SUPADATA_BASE_URL: str = "https://api.supadata.ai/v1"
    SUPADATA_MODE: str = "auto"
    SUPADATA_TIMEOUT_SECONDS: float = 30.0
    SUPADATA_MAX_ATTEMPTS: int = 3
    SUPADATA_RETRY_BASE_SECONDS: float = 1.0
    SUPADATA_RETRY_MAX_SECONDS: float = 8.0
    SUPADATA_POLL_INTERVAL_SECONDS: float = 1.0
    SUPADATA_MAX_POLL_ATTEMPTS: int = 90
    RAPIDAPI_KEY: str = ""
    RAPIDAPI_HOST: str = "youtube-transcript3.p.rapidapi.com"
    RAPIDAPI_BASE_URL: str = ""
    RAPIDAPI_TIMEOUT_SECONDS: float = 10.0
    RAPIDAPI_MAX_ATTEMPTS: int = 1
    RAPIDAPI_RETRY_BASE_SECONDS: float = 1.0
    RAPIDAPI_RETRY_MAX_SECONDS: float = 8.0
    RAPIDAPI_FALLBACK_TO_AUTO_LANGUAGE: bool = False

    DATA_DIR: str = "./data"
    OUTPUT_DIR: str = "./dumps"
    DATABASE_FILENAME: str = "transcript_harvester.db"
    MISSING_TRANSCRIPT_CACHE_SECONDS: int = 21600

    DEFAULT_MAX_VIDEOS: int = 3
    DEFAULT_LANGUAGES: list[str] = ["en"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TH_",
        extra="ignore",
    )

    @property
    def database_path(self) -> Path:
        return Path(self.DATA_DIR) / self.DATABASE_FILENAME

    @property
    def rapidapi_base_url(self) -> str:
        if self.RAPIDAPI_BASE_URL:
            return self.RAPIDAPI_BASE_URL.rstrip("/")
        return f"https://{self.RAPIDAPI_HOST}".rstrip("/")


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()

    # Allow plain YOUTUBE_API_KEY from the shell if TH_YOUTUBE_API_KEY is not set.
    if not settings.YOUTUBE_API_KEY:
        settings.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

    # Allow plain RAPIDAPI_KEY from the shell if TH_RAPIDAPI_KEY is not set.
    if not settings.RAPIDAPI_KEY:
        settings.RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

    # Allow plain SUPADATA_API_KEY from the shell if TH_SUPADATA_API_KEY is not set.
    if not settings.SUPADATA_API_KEY:
        settings.SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY", "")

    return settings

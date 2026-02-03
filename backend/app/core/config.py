from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Expert Suitability Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ese_db"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/ese_db"
    
    # YouTube API
    YOUTUBE_API_KEY: str = ""
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    
    # Scoring defaults
    DEFAULT_CREDIBILITY_WEIGHT: float = 0.2
    DEFAULT_TOPIC_AUTHORITY_WEIGHT: float = 0.3
    DEFAULT_COMMUNICATION_WEIGHT: float = 0.2
    DEFAULT_FRESHNESS_WEIGHT: float = 0.15
    DEFAULT_GROWTH_WEIGHT: float = 0.15
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


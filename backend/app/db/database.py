from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Convert postgres:// or postgresql:// to postgresql+asyncpg://
database_url = settings.DATABASE_URL
logger.info(f"🗄️  Database: Configuring connection")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    logger.info("   → Converted postgres:// to postgresql+asyncpg://")
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    logger.info("   → Converted postgresql:// to postgresql+asyncpg://")

logger.info(f"   → Creating async engine (echo={settings.DEBUG})")
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    future=True,
)
logger.info("   ✓ Database engine created")

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    logger.debug("🗄️  Creating new database session")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            logger.debug("   ✓ Session committed successfully")
        except Exception as e:
            logger.error(f"   ❌ Database session error: {e}")
            await session.rollback()
            logger.error("   ↶ Session rolled back")
            raise
        finally:
            await session.close()
            logger.debug("   ✓ Session closed")


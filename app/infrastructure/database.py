import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    DB_INITIALIZED = True
    logger.info("Database engine created: %s", settings.DATABASE_URL.split("://")[0])
except Exception as e:
    logger.critical("Failed to initialize database: %s", e)
    DB_INITIALIZED = False
    engine = None
    AsyncSessionLocal = None


async def get_db():
    """Dependency that yields an async DB session."""
    if not DB_INITIALIZED or AsyncSessionLocal is None:
        raise RuntimeError(
            "Database is not initialized. Check DATABASE_URL and ensure "
            "the database is accessible."
        )
    async with AsyncSessionLocal() as session:
        yield session

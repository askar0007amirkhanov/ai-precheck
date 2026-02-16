from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

try:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    DB_INITIALIZED = True
except Exception as e:
    print(f"CRITICAL: Failed to initialize database: {e}")
    DB_INITIALIZED = False
    engine = None
    AsyncSessionLocal = None

async def get_db():
    if not DB_INITIALIZED:
        print("WARNING: Database not initialized, yielding mock session")
        # Yield a mock context manager that does nothing
        class MockSession:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
        yield MockSession()
        return

    async with AsyncSessionLocal() as session:
        yield session

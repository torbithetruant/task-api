import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.database import Base, get_db
from app.main import app

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@test-db:5432/testdb")


@pytest.fixture(scope="session")
def event_loop():
    """Create one event loop for all tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create engine with no pooling to avoid connection reuse issues."""
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_engine):
    """Create client with proper session isolation."""
    async def override_get_db():
        # Create completely independent session for each request
        async_session = async_sessionmaker(
            db_engine, 
            class_=AsyncSession, 
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_data(db_engine):
    """Clean data between tests."""
    yield
    from sqlalchemy import text
    async with db_engine.connect() as conn:
        await conn.execute(text("TRUNCATE TABLE tasks RESTART IDENTITY CASCADE"))
        await conn.commit()
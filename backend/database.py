"""
Database configuration for PostgreSQL and Redis
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import redis.asyncio as redis
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# PostgreSQL configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://kennel:kennel_password@localhost:5432/kennel_db")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Redis configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Redis connection pool
redis_pool = None

async def get_redis():
    """Get Redis connection from pool"""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(REDIS_URL)
    return redis.Redis(connection_pool=redis_pool)

async def get_db():
    """Dependency to get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Close database connections"""
    global redis_pool
    await engine.dispose()
    if redis_pool:
        await redis_pool.disconnect()

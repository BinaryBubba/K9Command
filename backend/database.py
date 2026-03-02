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
# Try to use DATABASE_URL if set, otherwise construct from POSTGRES_* variables
if "DATABASE_URL" in os.environ:
    DATABASE_URL = os.environ["DATABASE_URL"]
else:
    # Construct from individual POSTGRES_* environment variables
    # Use 'postgres' as default host for Docker Compose networking
    pg_host = os.environ.get("POSTGRES_HOST", "postgres")
    pg_port = os.environ.get("POSTGRES_PORT", "5432")
    pg_user = os.environ.get("POSTGRES_USER", "myapp")
    pg_password = os.environ.get("POSTGRES_PASSWORD", "myapp_dev_password")
    pg_db = os.environ.get("POSTGRES_DB", "myapp")
    DATABASE_URL = f"postgresql+asyncpg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

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
# Use individual REDIS_* variables if available, otherwise construct from environment
redis_host = os.environ.get("REDIS_HOST", "redis")
redis_port = os.environ.get("REDIS_PORT", "6379")
REDIS_URL = os.environ.get("REDIS_URL", f"redis://{redis_host}:{redis_port}")

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


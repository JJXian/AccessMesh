"""异步数据库引擎、会话工厂与 FastAPI 会话依赖。"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from accessmesh.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """为单次请求提供会自动关闭的异步数据库会话。"""

    async with AsyncSessionLocal() as session:
        yield session

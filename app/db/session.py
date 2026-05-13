"""Database session management."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
    echo=settings.DEBUG,
    future=True,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncSession:
    """Get database session dependency."""
    async with async_session_maker() as session:
        yield session

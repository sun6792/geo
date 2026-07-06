"""Async SQLAlchemy engine and session management — PostgreSQL + SQLite compatible."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.config import settings

# Detect SQLite vs PostgreSQL
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Test database connectivity on startup. For SQLite, creates the file."""
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
            await conn.commit()
        return True
    except Exception:
        # For SQLite: file may not exist yet, but async engine creates it on connect
        try:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
                await conn.commit()
            return True
        except Exception:
            return False


async def init_db():
    """Create all tables on startup (for SQLite/local dev without migrations)."""
    if _is_sqlite:
        # Ensure ALL models are imported before table creation
        _import_all_models()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


def _import_all_models():
    """Pre-import all models to ensure complete metadata for table creation and FK resolution."""
    import app.models.customer  # noqa
    import app.models.account  # noqa
    import app.models.knowledge_base  # noqa
    import app.models.content  # noqa
    import app.models.review  # noqa
    import app.models.publish  # noqa
    import app.models.system  # noqa
    import app.models.agent  # noqa
    import app.models.billing  # noqa
    import app.models.template  # noqa

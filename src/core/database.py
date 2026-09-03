from typing import AsyncGenerator
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from src.config.settings import settings


class Base(DeclarativeBase):
    pass


class DatabaseManager:
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    def initialize(self):
        # Support sqlite+aiosqlite for local testing if requested
        db_url = settings.database_url
        logger.info(
            f"Initializing database engine: {db_url.split('@')[-1] if '@' in db_url else db_url}"
        )

        connect_args = {}
        if "sqlite" in db_url:
            connect_args = {"check_same_thread": False}

        self.engine = create_async_engine(
            db_url,
            echo=settings.db_echo,
            connect_args=connect_args,
            pool_pre_ping=True,
            **(
                {"pool_size": settings.db_pool_size, "max_overflow": settings.db_max_overflow}
                if "sqlite" not in db_url
                else {}
            ),
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self.session_factory:
            self.initialize()
        assert self.session_factory is not None
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_tables(self):
        if not self.engine:
            self.initialize()
        assert self.engine is not None
        # Ensure all models are imported so Base.metadata knows about them
        from src.models import (
            AdminNote,
            Quote,
            UserActivity,
            BlocklistTerm,
            BroadcastRecord,
            Group,
            GroupFilter,
            GroupMember,
            ModerationLog,
            UserProfileChange,
            TTLSettings,
            User,
        )

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            # Safe column migrations for existing PostgreSQL tables
            if "postgresql" in settings.database_url:
                try:
                    await conn.execute(
                        text(
                            "ALTER TABLE groups ADD COLUMN IF NOT EXISTS welcome_media_type VARCHAR(32);"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE groups ADD COLUMN IF NOT EXISTS welcome_media_file_id VARCHAR(512);"
                        )
                    )
                    await conn.execute(
                        text("ALTER TABLE groups ADD COLUMN IF NOT EXISTS welcome_buttons TEXT;")
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE groups ADD COLUMN IF NOT EXISTS english_only_enabled BOOLEAN DEFAULT FALSE;"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE groups ADD COLUMN IF NOT EXISTS tos_shield_enabled BOOLEAN DEFAULT TRUE;"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE groups ADD COLUMN IF NOT EXISTS locked_types TEXT DEFAULT '';"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE groups ADD COLUMN IF NOT EXISTS clean_service_enabled BOOLEAN DEFAULT FALSE;"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE groups ADD COLUMN IF NOT EXISTS antichannel_enabled BOOLEAN DEFAULT FALSE;"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE groups ADD COLUMN IF NOT EXISTS antichannel_mode VARCHAR(16) DEFAULT 'del';"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS likes_count INTEGER DEFAULT 0;"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE quotes ADD COLUMN IF NOT EXISTS dislikes_count INTEGER DEFAULT 0;"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS games_played INTEGER DEFAULT 0;"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS games_won INTEGER DEFAULT 0;"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS game_score INTEGER DEFAULT 0;"
                        )
                    )
                except Exception as e:
                    logger.debug(f"Column migration check note: {e}")

        logger.info("Database tables and schema migrations verified/created successfully.")

    async def close(self):
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine closed.")


db = DatabaseManager()

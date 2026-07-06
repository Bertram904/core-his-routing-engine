"""Async SQLAlchemy database connection and session lifecycle management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Final

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""


class DatabaseManager:
    """Encapsulated async database engine and session factory.

    Manages the full lifecycle of the SQLAlchemy async engine and provides
    secure, scoped session access via context managers and FastAPI-compatible
    dependency generators.

    Attributes:
        settings: Application settings supplying connection parameters.
    """

    _DEFAULT_SESSION_AUTOCOMMIT: Final[bool] = False
    _DEFAULT_SESSION_AUTOFLUSH: Final[bool] = False
    _DEFAULT_SESSION_EXPIRE_ON_COMMIT: Final[bool] = False

    def __init__(self, settings: Settings) -> None:
        """Initialize the manager without eagerly creating the engine.

        Args:
            settings: Validated application settings instance.
        """
        self._settings: Settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def settings(self) -> Settings:
        """Return the bound application settings."""
        return self._settings

    @property
    def engine(self) -> AsyncEngine:
        """Return the lazily initialized async engine.

        Returns:
            Active ``AsyncEngine`` instance.

        Raises:
            RuntimeError: If accessed after ``dispose`` has been called.
        """
        if self._engine is None:
            raise RuntimeError(
                "Database engine is not initialized. Call connect() first."
            )
        return self._engine

    @property
    def is_connected(self) -> bool:
        """Return whether the engine has been initialized and not disposed."""
        return self._engine is not None

    def connect(self) -> None:
        """Create the async engine and session factory.

        Idempotent: repeated calls are ignored while already connected.
        """
        if self._engine is not None:
            return

        self._engine = create_async_engine(
            self._settings.database_url,
            echo=self._settings.is_debug_enabled and self._settings.db_echo,
            pool_size=self._settings.db_pool_size,
            max_overflow=self._settings.db_max_overflow,
            pool_timeout=self._settings.db_pool_timeout_seconds,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            autocommit=self._DEFAULT_SESSION_AUTOCOMMIT,
            autoflush=self._DEFAULT_SESSION_AUTOFLUSH,
            expire_on_commit=self._DEFAULT_SESSION_EXPIRE_ON_COMMIT,
        )

    async def dispose(self) -> None:
        """Dispose the engine and release all pooled connections."""
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._session_factory = None

    def _create_session(self) -> AsyncSession:
        """Instantiate a new async session from the internal factory.

        Returns:
            A new ``AsyncSession`` bound to the active engine.

        Raises:
            RuntimeError: If the session factory has not been initialized.
        """
        if self._session_factory is None:
            raise RuntimeError(
                "Session factory is not initialized. Call connect() first."
            )
        return self._session_factory()

    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional async session with automatic cleanup.

        Commits on success, rolls back on exception, and always closes
        the session.

        Yields:
            An active ``AsyncSession`` within a transaction boundary.
        """
        session = self._create_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency that yields a request-scoped session.

        Rolls back uncommitted work on error and always closes the session.
        Callers are responsible for explicit ``commit()`` when needed.

        Yields:
            A request-bound ``AsyncSession``.
        """
        session = self._create_session()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


_database_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """Return the process-wide ``DatabaseManager`` singleton.

    Lazily constructs the manager on first access using cached settings.

    Returns:
        Shared ``DatabaseManager`` instance.
    """
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager(get_settings())
    return _database_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency wiring for database sessions.

    Ensures the global manager is connected before yielding a session.

    Yields:
        Request-scoped ``AsyncSession`` from the shared manager.
    """
    manager = get_database_manager()
    if not manager.is_connected:
        manager.connect()
    async for session in manager.get_session():
        yield session

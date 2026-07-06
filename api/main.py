"""FastAPI application entry point for the Core HIS simulation."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from api.routers.auth import router as auth_router
from api.routers.reception import router as reception_router
from core.config import Settings, get_settings
from infrastructure.cache.redis_client import get_redis_manager
from infrastructure.database import get_database_manager


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown of database and Redis connections.

    Yields:
        Control back to the application after resources are initialized.
    """
    database_manager = get_database_manager()
    redis_manager = get_redis_manager()

    database_manager.connect()
    await redis_manager.connect()

    yield

    await redis_manager.dispose()
    await database_manager.dispose()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance.

    Returns:
        Fully configured ``FastAPI`` application.
    """
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Core HIS — Hospital Information System simulation API.",
        lifespan=lifespan,
    )

    application.include_router(auth_router, prefix=settings.api_prefix)
    application.include_router(reception_router, prefix=settings.api_prefix)

    @application.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Return a simple liveness probe response."""
        return {"status": "ok"}

    @application.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        """Return basic API metadata."""
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
            "login": f"{settings.api_prefix}/auth/login",
        }

    return application


app = create_app()


def _run_dev_server() -> None:
    """Launch the development ASGI server when executed as ``__main__``."""
    import uvicorn

    settings: Settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_debug_enabled,
    )


if __name__ == "__main__":
    _run_dev_server()

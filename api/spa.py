"""SPA static file registration for the enterprise frontend."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def _frontend_dist_path() -> Path:
    """Resolve the built frontend distribution directory.

    Returns:
        Absolute path to ``frontend/dist``.
    """
    return Path(__file__).resolve().parent.parent / "frontend" / "dist"


def register_frontend(application: FastAPI) -> None:
    """Mount compiled frontend assets and SPA fallback routes when present.

    Args:
        application: FastAPI application instance.
    """
    dist_path = _frontend_dist_path()
    if not dist_path.exists():
        return

    assets_path = dist_path / "assets"
    if assets_path.is_dir():
        application.mount(
            "/assets",
            StaticFiles(directory=assets_path),
            name="frontend-assets",
        )

    index_file = dist_path / "index.html"
    reserved_prefixes = ("api/", "docs", "redoc", "openapi.json", "health")

    @application.get("/app", include_in_schema=False)
    async def spa_entry() -> FileResponse:
        """Serve the SPA shell for enterprise UI entry."""
        if not index_file.is_file():
            raise HTTPException(status_code=404, detail="Frontend not built")
        return FileResponse(index_file)

    @application.get("/{spa_path:path}", include_in_schema=False)
    async def spa_fallback(spa_path: str) -> FileResponse:
        """Serve static files or fall back to ``index.html`` for client routing."""
        if spa_path.startswith(reserved_prefixes) or spa_path in {
            "docs",
            "redoc",
            "openapi.json",
            "health",
        }:
            raise HTTPException(status_code=404)

        requested_file = dist_path / spa_path
        if spa_path and requested_file.is_file():
            return FileResponse(requested_file)

        if not index_file.is_file():
            raise HTTPException(status_code=404, detail="Frontend not built")
        return FileResponse(index_file)

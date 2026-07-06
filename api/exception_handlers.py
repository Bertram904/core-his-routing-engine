"""HTTP exception handlers mapping domain errors to API responses."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from domain.exceptions.domain_exceptions import AuthenticationError, EntityNotFoundError


def register_exception_handlers(application: FastAPI) -> None:
    """Register domain-to-HTTP exception translators on the FastAPI app.

    Args:
        application: FastAPI application instance.
    """

    @application.exception_handler(AuthenticationError)
    async def _handle_authentication_error(
        _request: Request,
        exc: AuthenticationError,
    ) -> JSONResponse:
        """Translate ``AuthenticationError`` to HTTP 401.

        Args:
            _request: Incoming HTTP request.
            exc: Raised authentication error.

        Returns:
            JSON error response with 401 status.
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message},
        )

    @application.exception_handler(EntityNotFoundError)
    async def _handle_entity_not_found(
        _request: Request,
        exc: EntityNotFoundError,
    ) -> JSONResponse:
        """Translate ``EntityNotFoundError`` to HTTP 404.

        Args:
            _request: Incoming HTTP request.
            exc: Raised not-found error.

        Returns:
            JSON error response with 404 status.
        """
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.message},
        )

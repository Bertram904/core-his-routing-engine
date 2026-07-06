"""Authentication and authorization FastAPI dependencies."""

from collections.abc import Callable, Sequence
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    SecurityScopes,
)

from application.services.auth_service import AuthService
from core.async_executor import run_blocking_io
from core.config import get_settings
from core.constants import AuthErrorDetail
from core.security import get_jwt_token_service, get_password_hasher
from domain.entities.token_payload import TokenPayload
from domain.interfaces import ITokenService
from infrastructure.cache.redis_client import get_redis_manager

_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_auth_service() -> AuthService:
    """Return a cached ``AuthService`` singleton.

    Returns:
        Configured authentication service.
    """
    return AuthService(
        settings=get_settings(),
        password_hasher=get_password_hasher(),
        token_service=get_jwt_token_service(),
        cache_client=get_redis_manager(),
    )


class PermissionChecker:
    """Reusable RBAC dependency verifying JWT scopes against required permissions."""

    def __init__(self, required_permissions: Sequence[str] | None = None) -> None:
        """Initialize the checker with optional static permission requirements.

        Args:
            required_permissions: Permission scopes that must be present in the JWT.
        """
        self._required_permissions: tuple[str, ...] = tuple(required_permissions or ())

    async def __call__(
        self,
        security_scopes: SecurityScopes,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(_bearer_scheme),
        ],
        token_service: Annotated[ITokenService, Depends(get_jwt_token_service)],
    ) -> TokenPayload:
        """Validate the bearer token and enforce fine-grained scope requirements.

        Args:
            security_scopes: Scopes declared via ``Security(..., scopes=[...])``.
            credentials: Bearer token extracted from the Authorization header.
            token_service: JWT decoding service interface.

        Returns:
            Decoded ``TokenPayload`` when all required scopes are granted.

        Raises:
            HTTPException: 401 when the token is missing or invalid.
            HTTPException: 403 when required scopes are not granted.
        """
        raw_token = self._extract_raw_token(credentials)
        payload = await self._decode_token_payload(token_service, raw_token)
        required_permissions = self._resolve_required_permissions(security_scopes)
        self._enforce_permissions(payload, required_permissions, security_scopes)
        return payload

    def _extract_raw_token(
        self,
        credentials: HTTPAuthorizationCredentials | None,
    ) -> str:
        """Extract the bearer token string from credentials.

        Args:
            credentials: Parsed Authorization header credentials.

        Returns:
            Raw JWT string.

        Raises:
            HTTPException: 401 when credentials are missing.
        """
        if credentials is None or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AuthErrorDetail.MISSING_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return credentials.credentials

    async def _decode_token_payload(
        self,
        token_service: ITokenService,
        raw_token: str,
    ) -> TokenPayload:
        """Decode a JWT using a non-blocking executor wrapper.

        Args:
            token_service: JWT service interface.
            raw_token: Encoded JWT string.

        Returns:
            Decoded ``TokenPayload``.

        Raises:
            HTTPException: 401 when decoding fails.
        """
        try:
            return await run_blocking_io(
                lambda: token_service.decode_access_token(raw_token)
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AuthErrorDetail.INVALID_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    def _resolve_required_permissions(
        self,
        security_scopes: SecurityScopes,
    ) -> tuple[str, ...]:
        """Merge static and SecurityScopes-declared permission requirements.

        Args:
            security_scopes: FastAPI security scopes from the endpoint decorator.

        Returns:
            Tuple of required permission scope strings.
        """
        if security_scopes.scopes:
            return tuple(security_scopes.scopes)
        return self._required_permissions

    def _enforce_permissions(
        self,
        payload: TokenPayload,
        required_permissions: tuple[str, ...],
        security_scopes: SecurityScopes,
    ) -> None:
        """Verify that every required permission exists in the token scopes.

        Args:
            payload: Decoded JWT payload.
            required_permissions: Scopes that must be present.
            security_scopes: FastAPI scopes for WWW-Authenticate header construction.

        Raises:
            HTTPException: 403 when a required scope is missing.
        """
        granted_scopes = set(payload.scopes)
        for permission in required_permissions:
            if permission not in granted_scopes:
                authenticate_value = self._build_authenticate_header(security_scopes)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=AuthErrorDetail.NOT_ENOUGH_PERMISSIONS,
                    headers={"WWW-Authenticate": authenticate_value},
                )

    def _build_authenticate_header(self, security_scopes: SecurityScopes) -> str:
        """Build a RFC 6750 WWW-Authenticate header value.

        Args:
            security_scopes: Active security scopes for the endpoint.

        Returns:
            Formatted ``Bearer`` challenge header value.
        """
        if security_scopes.scopes:
            return f'Bearer scope="{security_scopes.scope_str}"'
        return "Bearer"


def require_permissions(
    *permissions: str,
) -> Callable[..., Any]:
    """Factory returning a ``PermissionChecker`` for explicit permission lists.

    Args:
        *permissions: Required permission scope strings.

    Returns:
        Configured ``PermissionChecker`` instance.
    """
    return PermissionChecker(list(permissions))


AuthenticatedUser = Annotated[TokenPayload, Depends(PermissionChecker())]
ScopedUser = Annotated[TokenPayload, Security(PermissionChecker())]

__all__ = [
    "AuthenticatedUser",
    "AuthService",
    "PermissionChecker",
    "ScopedUser",
    "get_auth_service",
    "require_permissions",
]

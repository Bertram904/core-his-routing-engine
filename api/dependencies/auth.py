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
from core.config import get_settings
from core.constants import AuthErrorDetail
from core.security import (
    BcryptPasswordHasher,
    JwtTokenService,
    TokenPayload,
    get_jwt_token_service,
    get_password_hasher,
)
from infrastructure.cache.redis_client import RedisManager, get_redis_manager

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
        redis_manager=get_redis_manager(),
    )


class PermissionChecker:
    """Reusable RBAC dependency verifying JWT scopes against required permissions.

    Supports two invocation styles:

    * ``Depends(PermissionChecker(["write:clinical_record"]))``
    * ``Security(PermissionChecker(), scopes=["write:clinical_record"])``

    When a required permission is absent from the JWT ``scopes`` claim, raises
    HTTP 403 with detail ``"Not enough permissions"``.
    """

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
        token_service: Annotated[JwtTokenService, Depends(get_jwt_token_service)],
    ) -> TokenPayload:
        """Validate the bearer token and enforce fine-grained scope requirements.

        Args:
            security_scopes: Scopes declared via ``Security(..., scopes=[...])``.
            credentials: Bearer token extracted from the Authorization header.
            token_service: JWT decoding service.

        Returns:
            Decoded ``TokenPayload`` when all required scopes are granted.

        Raises:
            HTTPException: 401 when the token is missing or invalid.
            HTTPException: 403 when required scopes are not granted.
        """
        if credentials is None or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AuthErrorDetail.MISSING_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = token_service.decode_access_token(credentials.credentials)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AuthErrorDetail.INVALID_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        required_permissions = self._resolve_required_permissions(security_scopes)
        self._enforce_permissions(payload, required_permissions, security_scopes)
        return payload

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


# Type aliases for ergonomic endpoint annotations.
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

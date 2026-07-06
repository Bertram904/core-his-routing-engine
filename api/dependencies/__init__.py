"""Authentication and authorization dependency providers."""

from api.dependencies.auth import (
    AuthenticatedUser,
    PermissionChecker,
    ScopedUser,
    get_auth_service,
    require_permissions,
)

__all__ = [
    "AuthenticatedUser",
    "PermissionChecker",
    "ScopedUser",
    "get_auth_service",
    "require_permissions",
]

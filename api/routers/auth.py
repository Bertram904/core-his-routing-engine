"""Authentication HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import PermissionChecker, get_auth_service
from application.dtos.auth_dto import LoginRequest, TokenResponse
from application.services.auth_service import AuthService
from domain.entities.token_payload import TokenPayload
from infrastructure.database import get_db_session

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate a user and return a JWT with fine-grained permission scopes.

    Resolves ``User → Role → Permissions`` via a joined query on cache miss,
    caches the mapping in Redis, verifies credentials, and issues a JWT whose
    payload includes ``sub`` and ``scopes``.

    Args:
        request: Login credentials.
        session: Request-scoped async database session.
        auth_service: Authentication orchestration service.

    Returns:
        Signed JWT access token with embedded permission scopes.
    """
    return await auth_service.login(
        session=session,
        username=request.username,
        password=request.password,
    )


@router.get("/me")
async def get_current_user(
    token_payload: Annotated[TokenPayload, Depends(PermissionChecker())],
) -> dict[str, str | list[str]]:
    """Return the authenticated principal decoded from the JWT.

    Args:
        token_payload: Decoded JWT payload from the bearer token.

    Returns:
        Username and granted permission scopes.
    """
    return {
        "username": token_payload.subject,
        "scopes": list(token_payload.scopes),
    }


@router.get("/clinical-records/demo")
async def clinical_record_demo(
    token_payload: Annotated[
        TokenPayload,
        Security(PermissionChecker(), scopes=["write:clinical_record"]),
    ],
) -> dict[str, str]:
    """Demo protected endpoint requiring ``write:clinical_record`` scope.

    Args:
        token_payload: Decoded JWT after scope verification.

    Returns:
        Confirmation message for RBAC testing.
    """
    return {
        "message": "Access granted to clinical record write operation.",
        "username": token_payload.subject,
    }

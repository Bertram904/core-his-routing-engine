"""Reception-desk HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import PermissionChecker
from api.dependencies.reception import get_reception_service
from application.dtos.reception_dto import (
    PatientAutoPopulateResult,
    ReceptionIntakeRequest,
    ReceptionIntakeResult,
)
from application.services.reception_service import ReceptionService
from core.security import TokenPayload
from infrastructure.database import get_db_session

router = APIRouter(prefix="/reception", tags=["Reception"])


@router.get(
    "/auto-populate",
    response_model=PatientAutoPopulateResult,
)
async def auto_populate_patient(
    identity_number: Annotated[str, Query(min_length=1)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    reception_service: Annotated[ReceptionService, Depends(get_reception_service)],
    _: Annotated[
        TokenPayload,
        Security(PermissionChecker(), scopes=["read:patient"]),
    ],
) -> PatientAutoPopulateResult:
    """Auto-populate patient demographics by national identity number.

    Args:
        identity_number: National ID used for patient lookup.
        session: Request-scoped async database session.
        reception_service: Reception application service.
        _: Enforces ``read:patient`` scope via JWT.

    Returns:
        Auto-populate result with patient fields when found.
    """
    return await reception_service.auto_populate_by_identity_number(
        session=session,
        identity_number=identity_number,
    )


@router.post("/intake", response_model=ReceptionIntakeResult)
async def process_reception_intake(
    request: ReceptionIntakeRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    reception_service: Annotated[ReceptionService, Depends(get_reception_service)],
    _: Annotated[
        TokenPayload,
        Security(PermissionChecker(), scopes=["read:patient"]),
    ],
) -> ReceptionIntakeResult:
    """Process reception intake with auto-populate and dynamic routing.

    Args:
        request: Intake payload including identity number and routing context.
        session: Request-scoped async database session.
        reception_service: Reception application service.
        _: Enforces ``read:patient`` scope via JWT.

    Returns:
        Combined auto-populate and routing decision response.
    """
    return await reception_service.process_intake(
        session=session,
        request=request,
    )

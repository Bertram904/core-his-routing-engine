"""Reception-desk application service for auto-populate and intake routing."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dtos.reception_dto import (
    PatientAutoPopulateResult,
    ReceptionIntakeRequest,
    ReceptionIntakeResult,
)
from application.services.base_service import BaseService, IReceptionService
from application.services.routing_service import DynamicRoutingEngine
from domain.models import Patient


class ReceptionService(BaseService, IReceptionService):
    """Handles reception auto-populate and intake orchestration.

    Searches patients by ``identity_number`` to auto-populate demographic
    fields, then delegates dynamic routing to the injected
    ``DynamicRoutingEngine``. Contains no HTTP or framework dependencies.

    Attributes:
        routing_engine: Dynamic routing engine for workflow decisions.
    """

    def __init__(self, routing_engine: DynamicRoutingEngine) -> None:
        """Wire reception service dependencies.

        Args:
            routing_engine: Routing engine resolving target workflow stages.
        """
        self._routing_engine: DynamicRoutingEngine = routing_engine

    @property
    def routing_engine(self) -> DynamicRoutingEngine:
        """Return the bound dynamic routing engine."""
        return self._routing_engine

    async def auto_populate_by_identity_number(
        self,
        session: AsyncSession,
        identity_number: str,
    ) -> PatientAutoPopulateResult:
        """Search for a patient by identity number and return demographics.

        Because ``identity_number`` is encrypted at rest with Fernet, lookup
        decrypts candidates in the application layer after retrieval.

        Args:
            session: Active async database session.
            identity_number: National ID number to search.

        Returns:
            Auto-populate result indicating whether a patient was found.
        """
        normalized_identity = identity_number.strip()
        patient = await self._find_patient_by_identity_number(
            session,
            normalized_identity,
        )
        if patient is None:
            return PatientAutoPopulateResult(
                found=False,
                identity_number=normalized_identity,
            )

        return PatientAutoPopulateResult(
            found=True,
            patient_id=patient.id,
            name=patient.name,
            phone=patient.phone,
            identity_number=normalized_identity,
        )

    async def process_intake(
        self,
        session: AsyncSession,
        request: ReceptionIntakeRequest,
    ) -> ReceptionIntakeResult:
        """Process reception intake with auto-populate and dynamic routing.

        Args:
            session: Active async database session.
            request: Intake payload with identity number and routing context.

        Returns:
            Combined auto-populate and routing decision result.
        """
        auto_populate = await self.auto_populate_by_identity_number(
            session=session,
            identity_number=request.identity_number,
        )

        routing_context = request.routing_context
        if auto_populate.patient_id is not None:
            routing_context.patient_id = auto_populate.patient_id

        routing = await self._routing_engine.resolve_route(
            session=session,
            routing_context=routing_context,
        )
        return ReceptionIntakeResult(
            auto_populate=auto_populate,
            routing=routing,
        )

    async def _find_patient_by_identity_number(
        self,
        session: AsyncSession,
        identity_number: str,
    ) -> Patient | None:
        """Locate a patient by decrypted identity-number comparison.

        Args:
            session: Active async database session.
            identity_number: Plaintext national ID to match.

        Returns:
            Matching ``Patient`` or ``None``.
        """
        statement = select(Patient).where(Patient._identity_number.is_not(None))
        result = await session.execute(statement)
        for patient in result.scalars():
            if patient.identity_number == identity_number:
                return patient
        return None

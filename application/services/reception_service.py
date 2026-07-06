"""Reception-desk application service for auto-populate and intake routing."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dtos.reception_dto import (
    PatientAutoPopulateResult,
    ReceptionIntakeRequest,
    ReceptionIntakeResult,
    RoutingContextDto,
)
from application.services.base_service import IReceptionService
from application.services.interfaces import IRoutingEngine
from domain.models import Patient


class ReceptionService(IReceptionService):
    """Handles reception auto-populate and intake orchestration."""

    def __init__(self, routing_engine: IRoutingEngine) -> None:
        """Wire reception service dependencies.

        Args:
            routing_engine: Routing engine resolving target workflow stages.
        """
        self._routing_engine: IRoutingEngine = routing_engine

    async def auto_populate_by_identity_number(
        self,
        session: AsyncSession,
        identity_number: str,
    ) -> PatientAutoPopulateResult:
        """Search for a patient by identity number and return demographics.

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
            return self._build_not_found_result(normalized_identity)
        return self._build_found_result(patient, normalized_identity)

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
        routing_context = self._enrich_routing_context(
            request.routing_context,
            auto_populate.patient_id,
        )
        routing = await self._routing_engine.resolve_route(
            session=session,
            routing_context=routing_context,
        )
        return ReceptionIntakeResult(auto_populate=auto_populate, routing=routing)

    def _build_not_found_result(self, identity_number: str) -> PatientAutoPopulateResult:
        """Build a not-found auto-populate result.

        Args:
            identity_number: Queried identity number.

        Returns:
            Result indicating no matching patient.
        """
        return PatientAutoPopulateResult(found=False, identity_number=identity_number)

    def _build_found_result(
        self,
        patient: Patient,
        identity_number: str,
    ) -> PatientAutoPopulateResult:
        """Build a found auto-populate result from a patient entity.

        Args:
            patient: Matching patient ORM instance.
            identity_number: Queried identity number.

        Returns:
            Result with populated demographic fields.
        """
        return PatientAutoPopulateResult(
            found=True,
            patient_id=patient.id,
            name=patient.name,
            phone=patient.phone,
            identity_number=identity_number,
        )

    def _enrich_routing_context(
        self,
        routing_context: RoutingContextDto,
        patient_id: int | None,
    ) -> RoutingContextDto:
        """Attach a resolved patient ID to the routing context when available.

        Args:
            routing_context: Incoming routing context DTO.
            patient_id: Resolved patient identifier.

        Returns:
            Routing context with optional patient ID enrichment.
        """
        if patient_id is not None:
            routing_context.patient_id = patient_id
        return routing_context

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

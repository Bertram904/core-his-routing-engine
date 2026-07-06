"""Base contracts for application-layer services."""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from application.dtos.reception_dto import (
    PatientAutoPopulateResult,
    ReceptionIntakeResult,
    ReceptionIntakeRequest,
)


class BaseService(ABC):
    """Abstract base for all application services.

    Provides a common inheritance root enforcing consistent service
    boundaries across the application layer.
    """


class IReceptionService(BaseService):
    """Contract for reception-desk use cases."""

    @abstractmethod
    async def auto_populate_by_identity_number(
        self,
        session: AsyncSession,
        identity_number: str,
    ) -> PatientAutoPopulateResult:
        """Search for a patient by national identity number and auto-populate.

        Args:
            session: Active async database session.
            identity_number: National ID to search for.

        Returns:
            Auto-populate result with patient demographics when found.
        """

    @abstractmethod
    async def process_intake(
        self,
        session: AsyncSession,
        request: ReceptionIntakeRequest,
    ) -> ReceptionIntakeResult:
        """Process a reception intake with auto-populate and dynamic routing.

        Args:
            session: Active async database session.
            request: Reception intake payload.

        Returns:
            Combined auto-populate and routing decision result.
        """

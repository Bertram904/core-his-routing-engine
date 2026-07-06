"""Application-layer service contracts."""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from application.dtos.reception_dto import RoutingContextDto, RoutingDecisionDto


class IRoutingEngine(ABC):
    """Contract for dynamic patient workflow routing engines."""

    @abstractmethod
    async def resolve_route(
        self,
        session: AsyncSession,
        routing_context: RoutingContextDto,
    ) -> RoutingDecisionDto:
        """Resolve the highest-priority matching route for a context.

        Args:
            session: Active async database session.
            routing_context: Runtime routing facts.

        Returns:
            Routing decision describing the matched rule, if any.
        """

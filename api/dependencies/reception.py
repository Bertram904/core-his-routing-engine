"""Reception and routing FastAPI dependency providers."""

from functools import lru_cache

from application.services.interfaces import IRoutingEngine
from application.services.reception_service import ReceptionService
from application.services.routing_service import (
    DynamicRoutingEngine,
    JsonConditionRuleEvaluator,
)
from core.config import get_settings
from infrastructure.cache.redis_client import get_redis_manager


@lru_cache
def get_routing_engine() -> IRoutingEngine:
    """Return a cached routing engine singleton.

    Returns:
        ``IRoutingEngine`` implementation.
    """
    return DynamicRoutingEngine(
        settings=get_settings(),
        cache_client=get_redis_manager(),
        rule_evaluator=JsonConditionRuleEvaluator(),
    )


@lru_cache
def get_reception_service() -> ReceptionService:
    """Return a cached ``ReceptionService`` singleton.

    Returns:
        Configured reception application service.
    """
    return ReceptionService(routing_engine=get_routing_engine())


__all__ = [
    "get_reception_service",
    "get_routing_engine",
]

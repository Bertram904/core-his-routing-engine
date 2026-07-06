"""Dynamic patient routing engine with Redis-backed rule caching."""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dtos.reception_dto import (
    RoutingContextDto,
    RoutingDecisionDto,
    RoutingRuleSnapshot,
)
from core.config import Settings
from core.constants import RedisKeyPrefix
from domain.interfaces import AbstractRuleEvaluator
from domain.models import RoutingRule, WorkflowStage
from infrastructure.cache.redis_client import RedisManager


class JsonConditionRuleEvaluator(AbstractRuleEvaluator):
    """JSON key-value equality rule evaluator.

    ``condition_expression`` must be a JSON object whose keys are matched
    against the routing context using strict equality.

    Example expression::

        {"department": "emergency", "priority_level": "high"}
    """

    def evaluate(self, condition_expression: str, context: dict[str, Any]) -> bool:
        """Evaluate a JSON condition expression against a context mapping.

        Args:
            condition_expression: JSON-encoded condition object.
            context: Runtime routing facts.

        Returns:
            ``True`` when every condition key matches the context value.

        Raises:
            ValueError: When the expression is not valid JSON or not an object.
        """
        if not condition_expression.strip():
            return True

        try:
            conditions = json.loads(condition_expression)
        except json.JSONDecodeError as exc:
            raise ValueError("Rule condition_expression must be valid JSON.") from exc

        if not isinstance(conditions, dict):
            raise ValueError("Rule condition_expression must be a JSON object.")

        for key, expected_value in conditions.items():
            if context.get(key) != expected_value:
                return False
        return True


class DynamicRoutingEngine:
    """Evaluates routing rules with Redis-first caching and pluggable evaluators.

    The engine fetches active rules for a source stage from Redis when available,
    falls back to PostgreSQL on cache miss, and evaluates rules in priority order
    using any ``AbstractRuleEvaluator`` implementation (polymorphism).

    Attributes:
        settings: Application configuration.
        redis_manager: Redis cache adapter.
        rule_evaluator: Injected rule matching strategy.
    """

    def __init__(
        self,
        settings: Settings,
        redis_manager: RedisManager,
        rule_evaluator: AbstractRuleEvaluator,
    ) -> None:
        """Wire routing engine dependencies.

        Args:
            settings: Application settings.
            redis_manager: Redis manager for rule caching.
            rule_evaluator: Strategy for evaluating rule conditions.
        """
        self._settings: Settings = settings
        self._redis_manager: RedisManager = redis_manager
        self._rule_evaluator: AbstractRuleEvaluator = rule_evaluator

    @property
    def rule_evaluator(self) -> AbstractRuleEvaluator:
        """Return the active rule evaluator strategy."""
        return self._rule_evaluator

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
            ``RoutingDecisionDto`` describing the matched rule, if any.
        """
        rules = await self._get_cached_rules(session, routing_context.source_stage)
        evaluation_context = routing_context.to_evaluation_context()

        for rule in sorted(rules, key=lambda item: item.priority):
            if not rule.is_active:
                continue
            if self._rule_evaluator.evaluate(
                rule.condition_expression,
                evaluation_context,
            ):
                return RoutingDecisionDto(
                    matched=True,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    source_stage=rule.source_stage,
                    target_stage=rule.target_stage,
                )

        return RoutingDecisionDto(matched=False, source_stage=routing_context.source_stage)

    async def _get_cached_rules(
        self,
        session: AsyncSession,
        source_stage: WorkflowStage,
    ) -> list[RoutingRuleSnapshot]:
        """Fetch routing rules from Redis, falling back to PostgreSQL.

        Args:
            session: Active async database session.
            source_stage: Workflow stage used as the cache partition key.

        Returns:
            Ordered list of routing rule snapshots for the stage.
        """
        cache_key = self._build_cache_key(source_stage)
        cached_payload = await self._redis_manager.get(cache_key)
        if cached_payload is not None:
            raw_rules = json.loads(cached_payload)
            return [RoutingRuleSnapshot.model_validate(item) for item in raw_rules]

        rules = await self._load_rules_from_database(session, source_stage)
        await self._redis_manager.set(
            cache_key,
            json.dumps([rule.model_dump(mode="json") for rule in rules]),
            ttl_seconds=self._settings.routing_rules_cache_ttl_seconds,
        )
        return rules

    async def _load_rules_from_database(
        self,
        session: AsyncSession,
        source_stage: WorkflowStage,
    ) -> list[RoutingRuleSnapshot]:
        """Load active routing rules for a source stage from PostgreSQL.

        Args:
            session: Active async database session.
            source_stage: Workflow stage filter.

        Returns:
            Snapshot list suitable for caching and evaluation.
        """
        statement = (
            select(RoutingRule)
            .where(
                RoutingRule.source_stage == source_stage,
                RoutingRule.is_active.is_(True),
            )
            .order_by(RoutingRule.priority.asc())
        )
        result = await session.execute(statement)
        orm_rules = result.scalars().all()
        return [self._to_snapshot(rule) for rule in orm_rules]

    def _to_snapshot(self, rule: RoutingRule) -> RoutingRuleSnapshot:
        """Map an ORM routing rule to a cache-friendly snapshot.

        Args:
            rule: SQLAlchemy ``RoutingRule`` instance.

        Returns:
            ``RoutingRuleSnapshot`` DTO.
        """
        return RoutingRuleSnapshot(
            id=rule.id,
            name=rule.name,
            source_stage=rule.source_stage,
            target_stage=rule.target_stage,
            condition_expression=rule.condition_expression,
            priority=rule.priority,
            is_active=rule.is_active,
        )

    def _build_cache_key(self, source_stage: WorkflowStage) -> str:
        """Build the Redis cache key for a source stage rule set.

        Args:
            source_stage: Workflow stage partition.

        Returns:
            Namespaced Redis key.
        """
        return f"{RedisKeyPrefix.ROUTING_RULES}:{source_stage.value}"

"""Reception and routing data transfer objects."""

from typing import Any

from pydantic import BaseModel, Field

from domain.models import WorkflowStage


class PatientAutoPopulateResult(BaseModel):
    """Result of an identity-number auto-populate lookup.

    Attributes:
        found: Whether a matching patient exists.
        patient_id: Internal patient identifier when found.
        name: Patient full name.
        phone: Patient phone number.
        identity_number: Queried national identity number.
    """

    found: bool
    patient_id: int | None = None
    name: str | None = None
    phone: str | None = None
    identity_number: str


class RoutingContextDto(BaseModel):
    """Runtime facts supplied to the dynamic routing engine.

    Attributes:
        source_stage: Current workflow stage triggering routing.
        patient_id: Optional patient identifier.
        department: Requesting or assigned department.
        priority_level: Triage or urgency level.
        metadata: Additional key-value matching attributes.
    """

    source_stage: WorkflowStage
    patient_id: int | None = None
    department: str | None = None
    priority_level: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_evaluation_context(self) -> dict[str, Any]:
        """Flatten the DTO into a rule-evaluation context dictionary.

        Returns:
            Context mapping for ``AbstractRuleEvaluator``.
        """
        context: dict[str, Any] = {
            "source_stage": self.source_stage.value,
            "patient_id": self.patient_id,
            "department": self.department,
            "priority_level": self.priority_level,
        }
        context.update(self.metadata)
        return {key: value for key, value in context.items() if value is not None}


class RoutingDecisionDto(BaseModel):
    """Outcome of a dynamic routing evaluation.

    Attributes:
        matched: Whether a routing rule matched.
        rule_id: Identifier of the matched rule.
        rule_name: Human-readable rule name.
        source_stage: Stage that triggered evaluation.
        target_stage: Destination stage when matched.
    """

    matched: bool
    rule_id: int | None = None
    rule_name: str | None = None
    source_stage: WorkflowStage | None = None
    target_stage: WorkflowStage | None = None


class RoutingRuleSnapshot(BaseModel):
    """Serializable routing rule representation for Redis caching.

    Attributes:
        id: Rule primary key.
        name: Unique rule name.
        source_stage: Trigger workflow stage.
        target_stage: Destination workflow stage.
        condition_expression: Serialized condition DSL.
        priority: Evaluation priority (lower first).
        is_active: Whether the rule is eligible for matching.
    """

    id: int
    name: str
    source_stage: WorkflowStage
    target_stage: WorkflowStage
    condition_expression: str
    priority: int
    is_active: bool


class ReceptionIntakeRequest(BaseModel):
    """Payload for reception intake with routing context.

    Attributes:
        identity_number: Patient national ID for auto-populate.
        routing_context: Facts used by the routing engine.
    """

    identity_number: str = Field(min_length=1)
    routing_context: RoutingContextDto


class ReceptionIntakeResult(BaseModel):
    """Combined reception intake response.

    Attributes:
        auto_populate: Patient lookup result.
        routing: Dynamic routing decision.
    """

    auto_populate: PatientAutoPopulateResult
    routing: RoutingDecisionDto

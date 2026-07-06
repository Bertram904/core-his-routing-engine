"""Patient workflow list data transfer objects."""

from pydantic import BaseModel

from domain.models import WorkflowStage, WorkflowStatus


class WorkflowListItem(BaseModel):
    """Summary row for workflow selection in the enterprise UI.

    Attributes:
        id: Workflow primary key.
        patient_id: Associated patient identifier.
        patient_name: Patient display name.
        current_stage: Present workflow stage.
        status: Workflow lifecycle status.
        assigned_department: Department currently responsible.
    """

    id: int
    patient_id: int
    patient_name: str
    current_stage: WorkflowStage
    status: WorkflowStatus
    assigned_department: str | None

"""Clinical record data transfer objects."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from domain.models import ClinicalRecordStatus, WorkflowStage, WorkflowStatus


class DynamicClinicalRecordRequest(BaseModel):
    """Dynamic JSON payload for creating a clinical record.

    Known fields are validated explicitly; additional keys are preserved
    in the stored JSON content for schema-flexible clinical forms.

    Attributes:
        record_type: Clinical document category.
        title: Short record heading.
    """

    model_config = ConfigDict(extra="allow")

    record_type: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)


class ClinicalRecordResponse(BaseModel):
    """Response returned after persisting a clinical record.

    Attributes:
        id: Created record primary key.
        workflow_id: Associated workflow identifier.
        patient_id: Subject patient identifier.
        author_id: Authoring user identifier.
        record_type: Clinical document category.
        title: Record heading.
        content: Serialized dynamic JSON payload.
        status: Publication lifecycle status.
        created_at: Creation timestamp.
    """

    id: int
    workflow_id: int
    patient_id: int
    author_id: int
    record_type: str
    title: str
    content: str
    status: ClinicalRecordStatus
    created_at: datetime


class ClinicalRecordExportItem(BaseModel):
    """Single clinical record entry embedded in a PDF export."""

    record_type: str
    title: str
    content: dict[str, Any]
    status: str
    created_at: str


class WorkflowPdfContext(BaseModel):
    """Template context for workflow PDF export."""

    workflow_id: int
    patient_id: int
    patient_name: str
    current_stage: WorkflowStage
    workflow_status: WorkflowStatus
    assigned_department: str | None
    records: list[ClinicalRecordExportItem]

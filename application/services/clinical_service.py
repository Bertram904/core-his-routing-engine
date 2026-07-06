"""Clinical record application service."""

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from application.dtos.clinical_dto import (
    ClinicalRecordExportItem,
    ClinicalRecordResponse,
    DynamicClinicalRecordRequest,
    WorkflowPdfContext,
)
from application.services.base_service import BaseService
from core.constants import ClinicalErrorDetail
from domain.models import (
    ClinicalRecord,
    ClinicalRecordStatus,
    PatientWorkflow,
    User,
)


class ClinicalService(BaseService):
    """Orchestrates clinical record persistence and PDF export context building.

    Contains pure application logic with no HTTP framework dependencies.

    Attributes:
        None — stateless service resolved per request via dependency injection.
    """

    async def create_workflow_record(
        self,
        session: AsyncSession,
        workflow_id: int,
        author_username: str,
        request: DynamicClinicalRecordRequest,
    ) -> ClinicalRecordResponse:
        """Persist a clinical record for a workflow using a dynamic JSON payload.

        Args:
            session: Active async database session.
            workflow_id: Target workflow primary key.
            author_username: JWT subject identifying the authoring user.
            request: Dynamic clinical record payload.

        Returns:
            Persisted record response DTO.

        Raises:
            HTTPException: 404 when workflow or author is not found.
        """
        workflow = await self._get_workflow(session, workflow_id)
        if workflow is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ClinicalErrorDetail.WORKFLOW_NOT_FOUND,
            )

        author = await self._get_user_by_username(session, author_username)
        if author is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ClinicalErrorDetail.AUTHOR_NOT_FOUND,
            )

        content_payload = self._serialize_dynamic_payload(request)
        clinical_record = ClinicalRecord(
            patient_id=workflow.patient_id,
            author_id=author.id,
            record_type=request.record_type,
            title=request.title,
            content=content_payload,
            status=ClinicalRecordStatus.DRAFT,
        )
        session.add(clinical_record)
        await session.flush()
        await session.refresh(clinical_record)

        return ClinicalRecordResponse(
            id=clinical_record.id,
            workflow_id=workflow_id,
            patient_id=clinical_record.patient_id,
            author_id=clinical_record.author_id,
            record_type=clinical_record.record_type,
            title=clinical_record.title,
            content=clinical_record.content,
            status=clinical_record.status,
            created_at=clinical_record.created_at,
        )

    async def build_workflow_pdf_context(
        self,
        session: AsyncSession,
        workflow_id: int,
    ) -> WorkflowPdfContext:
        """Build the PDF template context for a workflow export.

        Args:
            session: Active async database session.
            workflow_id: Target workflow primary key.

        Returns:
            ``WorkflowPdfContext`` for template rendering.

        Raises:
            HTTPException: 404 when the workflow is not found.
        """
        workflow = await self._get_workflow_with_patient(session, workflow_id)
        if workflow is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ClinicalErrorDetail.WORKFLOW_NOT_FOUND,
            )

        records = await self._get_patient_clinical_records(
            session,
            workflow.patient_id,
        )
        export_records = [
            ClinicalRecordExportItem(
                record_type=record.record_type,
                title=record.title,
                content=self._deserialize_content(record.content),
                status=record.status.value,
                created_at=record.created_at.isoformat(),
            )
            for record in records
        ]

        return WorkflowPdfContext(
            workflow_id=workflow.id,
            patient_id=workflow.patient_id,
            patient_name=workflow.patient.name,
            current_stage=workflow.current_stage,
            workflow_status=workflow.status,
            assigned_department=workflow.assigned_department,
            records=export_records,
        )

    async def _get_workflow(
        self,
        session: AsyncSession,
        workflow_id: int,
    ) -> PatientWorkflow | None:
        """Fetch a workflow by primary key.

        Args:
            session: Active async database session.
            workflow_id: Workflow identifier.

        Returns:
            ``PatientWorkflow`` or ``None``.
        """
        return await session.get(PatientWorkflow, workflow_id)

    async def _get_workflow_with_patient(
        self,
        session: AsyncSession,
        workflow_id: int,
    ) -> PatientWorkflow | None:
        """Fetch a workflow with its related patient eagerly loaded.

        Args:
            session: Active async database session.
            workflow_id: Workflow identifier.

        Returns:
            ``PatientWorkflow`` with patient, or ``None``.
        """
        statement = (
            select(PatientWorkflow)
            .options(joinedload(PatientWorkflow.patient))
            .where(PatientWorkflow.id == workflow_id)
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def _get_user_by_username(
        self,
        session: AsyncSession,
        username: str,
    ) -> User | None:
        """Resolve an authoring user by username.

        Args:
            session: Active async database session.
            username: Login identifier from JWT ``sub`` claim.

        Returns:
            Matching ``User`` or ``None``.
        """
        statement = select(User).where(User.username == username)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def _get_patient_clinical_records(
        self,
        session: AsyncSession,
        patient_id: int,
    ) -> list[ClinicalRecord]:
        """Load all clinical records for a patient ordered by creation time.

        Args:
            session: Active async database session.
            patient_id: Patient identifier.

        Returns:
            Ordered list of clinical records.
        """
        statement = (
            select(ClinicalRecord)
            .where(ClinicalRecord.patient_id == patient_id)
            .order_by(ClinicalRecord.created_at.asc())
        )
        result = await session.execute(statement)
        return list(result.scalars().all())

    def _serialize_dynamic_payload(
        self,
        request: DynamicClinicalRecordRequest,
    ) -> str:
        """Serialize the dynamic request body to a JSON string for storage.

        Args:
            request: Dynamic clinical record request.

        Returns:
            JSON string preserving all submitted fields.
        """
        payload: dict[str, Any] = request.model_dump(mode="json")
        return json.dumps(payload, ensure_ascii=False)

    def _deserialize_content(self, content: str) -> dict[str, Any]:
        """Deserialize stored record content into a dictionary.

        Args:
            content: JSON string from the database.

        Returns:
            Parsed content dictionary.
        """
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return {"raw_content": content}
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}

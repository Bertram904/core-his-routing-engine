"""Clinical workflow HTTP routes."""

from io import BytesIO
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Security, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import PermissionChecker
from api.dependencies.clinical import get_clinical_service, get_pdf_generator
from application.dtos.clinical_dto import (
    ClinicalRecordResponse,
    DynamicClinicalRecordRequest,
)
from application.services.clinical_service import ClinicalService
from core.constants import PdfDefaults
from core.security import TokenPayload
from domain.interfaces import IPdfGenerator
from infrastructure.database import get_db_session

router = APIRouter(tags=["Clinical"])


@router.post(
    "/workflows/{workflow_id}/record",
    response_model=ClinicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_clinical_record(
    workflow_id: int,
    request: DynamicClinicalRecordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    clinical_service: Annotated[ClinicalService, Depends(get_clinical_service)],
    token_payload: Annotated[
        TokenPayload,
        Security(PermissionChecker(), scopes=["write:clinical_record"]),
    ],
) -> ClinicalRecordResponse:
    """Create a clinical record for a workflow from a dynamic JSON payload.

    Additional JSON fields beyond ``record_type`` and ``title`` are preserved
    in the stored record content.

    Args:
        workflow_id: Target patient workflow identifier.
        request: Dynamic clinical record body.
        session: Request-scoped async database session.
        clinical_service: Clinical application service.
        token_payload: Authenticated principal from JWT.

    Returns:
        Persisted clinical record metadata.
    """
    record = await clinical_service.create_workflow_record(
        session=session,
        workflow_id=workflow_id,
        author_username=token_payload.subject,
        request=request,
    )
    await session.commit()
    return record


@router.get("/workflows/{workflow_id}/export-pdf")
async def export_workflow_pdf(
    workflow_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    clinical_service: Annotated[ClinicalService, Depends(get_clinical_service)],
    pdf_generator: Annotated[IPdfGenerator, Depends(get_pdf_generator)],
    _: Annotated[
        TokenPayload,
        Security(PermissionChecker(), scopes=["read:patient"]),
    ],
) -> StreamingResponse:
    """Export a workflow and its clinical records as a PDF document.

    Args:
        workflow_id: Target patient workflow identifier.
        session: Request-scoped async database session.
        clinical_service: Clinical application service.
        pdf_generator: Injected ``IPdfGenerator`` implementation.
        _: Enforces ``read:patient`` scope via JWT.

    Returns:
        ``StreamingResponse`` streaming the generated PDF bytes.
    """
    pdf_context_model = await clinical_service.build_workflow_pdf_context(
        session=session,
        workflow_id=workflow_id,
    )
    template_context: dict[str, Any] = pdf_context_model.model_dump(mode="json")

    pdf_bytes = await pdf_generator.generate(
        template_name=PdfDefaults.CLINICAL_WORKFLOW_TEMPLATE,
        context=template_context,
    )

    filename = f"workflow-{workflow_id}-clinical-report.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=PdfDefaults.MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

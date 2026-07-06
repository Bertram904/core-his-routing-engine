"""Clinical workflow FastAPI dependency providers."""

from functools import lru_cache

from application.services.clinical_service import ClinicalService
from domain.interfaces import IPdfGenerator
from infrastructure.pdf_generator import get_weasyprint_pdf_generator


@lru_cache
def get_clinical_service() -> ClinicalService:
    """Return a cached ``ClinicalService`` singleton.

    Returns:
        Configured clinical application service.
    """
    return ClinicalService()


def get_pdf_generator() -> IPdfGenerator:
    """Return the ``IPdfGenerator`` implementation for dependency injection.

    The concrete ``WeasyPrintPdfGenerator`` is resolved here so endpoints
    depend only on the ``IPdfGenerator`` interface (Dependency Inversion).

    Returns:
        PDF generator satisfying ``IPdfGenerator``.
    """
    return get_weasyprint_pdf_generator()


__all__ = [
    "get_clinical_service",
    "get_pdf_generator",
]

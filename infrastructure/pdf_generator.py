"""WeasyPrint-backed PDF generator implementing ``IPdfGenerator``."""

import asyncio
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from weasyprint import HTML

from core.constants import PdfDefaults
from domain.interfaces import IPdfGenerator


class WeasyPrintPdfGenerator(IPdfGenerator):
    """PDF generator using Jinja2 templates and WeasyPrint rendering.

    Template rendering is encapsulated in the private ``_render_html_template``
    method. Consumers depend on ``IPdfGenerator``, not this concrete class.

    Attributes:
        template_dir: Directory containing Jinja2 HTML templates.
    """

    _TEMPLATE_DIR_NAME: Final[str] = "templates"

    def __init__(self, template_dir: Path) -> None:
        """Initialize the generator with a template directory.

        Args:
            template_dir: Filesystem path to Jinja2 templates.

        Raises:
            ValueError: If the template directory does not exist.
        """
        if not template_dir.is_dir():
            raise ValueError(f"Template directory not found: {template_dir}")

        self._template_dir: Path = template_dir
        self._jinja_environment: Environment = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )
        self._jinja_environment.filters["tojson"] = self._json_pretty_filter

    @property
    def template_dir(self) -> Path:
        """Return the bound template directory path."""
        return self._template_dir

    async def generate(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> bytes:
        """Render a PDF from a named Jinja2 template and context data.

        Args:
            template_name: Logical template identifier (without extension).
            context: Key-value pairs injected into the template.

        Returns:
            Raw PDF document bytes.

        Raises:
            ValueError: When template rendering or PDF conversion fails.
        """
        if not template_name:
            raise ValueError("template_name cannot be empty.")

        html_content = self._render_html_template(template_name, context)
        return await self.generate_from_html(html_content)

    async def generate_from_html(self, html_content: str) -> bytes:
        """Render a PDF directly from an HTML string using WeasyPrint.

        Args:
            html_content: Fully composed HTML markup.

        Returns:
            Raw PDF document bytes.

        Raises:
            ValueError: When ``html_content`` is empty.
        """
        if not html_content.strip():
            raise ValueError("html_content cannot be empty.")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._write_pdf_bytes, html_content)

    def _render_html_template(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """Render a Jinja2 template to HTML (private encapsulation).

        Args:
            template_name: Template file stem (``.html`` appended automatically).
            context: Template context variables.

        Returns:
            Rendered HTML string.

        Raises:
            ValueError: When the template cannot be found or rendered.
        """
        template_file = f"{template_name}{PdfDefaults.TEMPLATE_EXTENSION}"
        try:
            template = self._jinja_environment.get_template(template_file)
        except TemplateNotFound as exc:
            raise ValueError(f"Template '{template_file}' not found.") from exc

        return template.render(**context)

    @staticmethod
    def _json_pretty_filter(value: Any, indent: int = 2) -> str:
        """Jinja2 filter rendering a value as indented JSON.

        Args:
            value: Value to serialize.
            indent: JSON indentation width.

        Returns:
            Pretty-printed JSON string.
        """
        return json.dumps(value, indent=indent, ensure_ascii=False)

    def _write_pdf_bytes(self, html_content: str) -> bytes:
        """Synchronously convert HTML to PDF bytes via WeasyPrint.

        Args:
            html_content: Rendered HTML markup.

        Returns:
            PDF binary content.
        """
        return HTML(string=html_content).write_pdf()


@lru_cache
def get_weasyprint_pdf_generator() -> WeasyPrintPdfGenerator:
    """Return a cached ``WeasyPrintPdfGenerator`` singleton.

    Returns:
        Configured PDF generator bound to the infrastructure templates directory.
    """
    template_dir = Path(__file__).resolve().parent / WeasyPrintPdfGenerator._TEMPLATE_DIR_NAME
    return WeasyPrintPdfGenerator(template_dir=template_dir)

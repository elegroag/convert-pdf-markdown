"""MD2DOCX Converter.

A Hexagonal Architecture library for converting Markdown manuals
to structured Word (.docx) documents.
"""

from md2docx.application.dto.dtos import ConversionRequest, ConversionResult, InspectionResult
from md2docx.application.services.conversion_service import ConversionService
from md2docx.domain.entities.entities import ConsolidatedManual, DocxBuild, MarkdownSection
from md2docx.domain.value_objects.value_objects import ConversionConfig

__version__ = "0.1.0"

__all__ = [
    "ConsolidatedManual",
    "ConversionConfig",
    "ConversionRequest",
    "ConversionResult",
    "ConversionService",
    "DocxBuild",
    "InspectionResult",
    "MarkdownSection",
    "__version__",
]

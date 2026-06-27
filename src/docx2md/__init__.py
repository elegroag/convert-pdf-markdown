"""DOCX2MD Converter.

A Hexagonal Architecture library for converting Word documents
to structured Markdown.
"""

from docx2md.application.dto.dtos import (
    ConversionRequest,
    ConversionResult,
    InspectionResult,
)
from docx2md.application.services.conversion_service import ConversionService
from docx2md.domain.entities.entities import (
    DocumentBlock,
    DocxDocument,
    DocxMetadata,
    HeadingBlock,
    HorizontalRuleBlock,
    ImageBlock,
    ListItemBlock,
    MarkdownDocument,
    ParagraphBlock,
    TableBlock,
)
from docx2md.domain.value_objects.value_objects import ConversionConfig

__version__ = "0.1.0"

__all__ = [
    "ConversionConfig",
    "ConversionRequest",
    "ConversionResult",
    "ConversionService",
    "DocxDocument",
    "DocxMetadata",
    "DocumentBlock",
    "HeadingBlock",
    "HorizontalRuleBlock",
    "ImageBlock",
    "InspectionResult",
    "ListItemBlock",
    "MarkdownDocument",
    "ParagraphBlock",
    "TableBlock",
    "__version__",
]

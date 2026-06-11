"""PDF2MD Converter.

A Hexagonal Architecture library for converting PDF books and documents
to structured Markdown.
"""

from pdf2md.application.dto.dtos import (
    ConversionRequest,
    ConversionResult,
)
from pdf2md.application.services.conversion_service import ConversionService
from pdf2md.domain.entities.entities import (
    ImageAsset,
    MarkdownDocument,
    MarkdownPage,
    PdfDocument,
    PdfMetadata,
    PdfPage,
    TableNode,
)
from pdf2md.domain.value_objects.value_objects import ConversionConfig

__version__ = "0.1.0"

__all__ = [
    "ConversionConfig",
    "ConversionRequest",
    "ConversionResult",
    "ConversionService",
    "ImageAsset",
    "MarkdownDocument",
    "MarkdownPage",
    "PdfDocument",
    "PdfMetadata",
    "PdfPage",
    "TableNode",
    "__version__",
]

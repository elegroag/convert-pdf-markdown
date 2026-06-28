"""XLSX2MD Converter."""

from xlsx2md.application.dto.dtos import (
    ConversionRequest,
    ConversionResult,
    InspectionResult,
)
from xlsx2md.application.services.conversion_service import ConversionService
from xlsx2md.domain.entities.entities import (
    CellBlock,
    ImageBlock,
    MarkdownDocument,
    SheetBlock,
    XlsxDocument,
    XlsxMetadata,
)
from xlsx2md.domain.value_objects.value_objects import ConversionConfig

__version__ = "0.1.0"

__all__ = [
    "CellBlock",
    "ConversionConfig",
    "ConversionRequest",
    "ConversionResult",
    "ConversionService",
    "ImageBlock",
    "InspectionResult",
    "MarkdownDocument",
    "SheetBlock",
    "XlsxDocument",
    "XlsxMetadata",
    "__version__",
]

"""PDF extractor adapters (Hexagonal infrastructure)."""

from pdf2md.infrastructure.extractors.camelot_extractor import (
    CamelotTableExtractor,
)
from pdf2md.infrastructure.extractors.pdfplumber_extractor import (
    PdfplumberTableExtractor,
)
from pdf2md.infrastructure.extractors.pymupdf_extractor import (
    PymupdfExtractor,
    PyMuPdfExtractor,
    build_default_table_extractor,
)

__all__ = [
    "CamelotTableExtractor",
    "PdfplumberTableExtractor",
    "PymupdfExtractor",
    "PyMuPdfExtractor",
    "build_default_table_extractor",
]

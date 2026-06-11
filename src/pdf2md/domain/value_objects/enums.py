"""Domain value objects for PDF2MD.

Pure data containers, immutable where appropriate, with no dependencies
on infrastructure libraries. These represent concepts that are identified
by their attributes rather than identity.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class BlockType(str, Enum):
    """Semantic type of a content block within a PDF page."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE = "code"
    LIST_ITEM = "list_item"


class HeadingStyle(str, Enum):
    """Markdown heading style for the output document."""

    ATX = "atx"  # # Heading
    SETEXT = "setext"  # Heading\n=======


class TableEngine(str, Enum):
    """Engine to use for table extraction."""

    PDFPLUMBER = "pdfplumber"
    CAMELOT = "camelot"


class ExtractorEngine(str, Enum):
    """Engine to use for the primary PDF extraction."""

    PYMUPDF = "pymupdf"
    PDFPLUMBER = "pdfplumber"

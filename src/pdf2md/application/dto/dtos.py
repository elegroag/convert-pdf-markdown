"""Application DTOs (Data Transfer Objects).

DTOs cross the boundary between the application and its callers. They
intentionally duplicate only the data callers need, decoupling the
public API from the domain model.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pdf2md.domain.value_objects.value_objects import ConversionConfig


@dataclass(frozen=True)
class ConversionRequest:
    """Public DTO for a single conversion request.

    Attributes:
        pdf_path: Path of the source PDF.
        output_dir: Directory where Markdown and assets will be written.
        config: Optional conversion configuration override.
        password: Optional password for encrypted PDFs.
    """

    pdf_path: Path
    output_dir: Path
    config: ConversionConfig | None = None
    password: str | None = None


@dataclass(frozen=True)
class ConversionResult:
    """Public DTO for a single conversion result.

    Attributes:
        status: ``"success"`` or ``"error"``.
        output_path: Path of the generated ``.md`` file (when successful).
        image_count: Number of images written to disk.
        table_count: Number of tables rendered.
        page_count: Total number of pages processed.
        elapsed_seconds: Wall-clock time for the conversion.
        error: Exception class name on failure.
        error_message: Human-readable error description.
    """

    status: str
    output_path: Path | None = None
    image_count: int = 0
    table_count: int = 0
    page_count: int = 0
    elapsed_seconds: float = 0.0
    error: str | None = None
    error_message: str = ""


@dataclass(frozen=True)
class InspectionResult:
    """Result of ``inspect`` — structure of a PDF without full conversion.

    Attributes:
        file_path: The source PDF.
        page_count: Number of pages.
        metadata: A dict with title, author, etc.
        heading_counts: Number of headings per level (1-6).
        image_count: Total images detected.
        table_count: Total tables detected.
    """

    file_path: Path
    page_count: int
    metadata: dict
    heading_counts: dict[int, int]
    image_count: int
    table_count: int

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict."""
        return {
            "file_path": str(self.file_path),
            "page_count": self.page_count,
            "metadata": self.metadata,
            "heading_counts": {str(k): v for k, v in self.heading_counts.items()},
            "image_count": self.image_count,
            "table_count": self.table_count,
        }

"""Application DTOs for DOCX2MD."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx2md.domain.value_objects.value_objects import ConversionConfig


@dataclass(frozen=True)
class ConversionRequest:
    """Public DTO for a single conversion request."""

    docx_path: Path
    output_dir: Path
    config: ConversionConfig | None = None


@dataclass(frozen=True)
class ConversionResult:
    """Public DTO for a single conversion result."""

    status: str
    output_path: Path | None = None
    total_blocks: int = 0
    headings: int = 0
    paragraphs: int = 0
    tables: int = 0
    images: int = 0
    list_items: int = 0
    elapsed_seconds: float = 0.0
    error: str | None = None
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict."""
        return {
            "status": self.status,
            "output_path": str(self.output_path) if self.output_path else None,
            "total_blocks": self.total_blocks,
            "headings": self.headings,
            "paragraphs": self.paragraphs,
            "tables": self.tables,
            "images": self.images,
            "list_items": self.list_items,
            "elapsed_seconds": self.elapsed_seconds,
            "error": self.error,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class InspectionResult:
    """Result of inspect — structure without full conversion."""

    file_path: Path
    total_blocks: int
    heading_counts: dict[int, int]
    paragraph_count: int
    image_count: int
    table_count: int
    list_item_count: int

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict."""
        return {
            "file_path": str(self.file_path),
            "total_blocks": self.total_blocks,
            "heading_counts": {str(k): v for k, v in self.heading_counts.items()},
            "paragraph_count": self.paragraph_count,
            "image_count": self.image_count,
            "table_count": self.table_count,
            "list_item_count": self.list_item_count,
        }

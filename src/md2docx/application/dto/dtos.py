"""Application DTOs for MD2DOCX."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from md2docx.domain.value_objects.value_objects import ConversionConfig


@dataclass(frozen=True)
class ConversionRequest:
    """Public DTO for a single conversion request."""

    output_dir: Path
    md_path: Path | None = None
    source_paths: tuple[Path, ...] = ()
    config: ConversionConfig | None = None


@dataclass(frozen=True)
class ConversionResult:
    """Public DTO for a single conversion result."""

    status: str
    docx_path: Path | None = None
    md_path: Path | None = None
    sections: int = 0
    refined: bool = False
    elapsed_seconds: float = 0.0
    error: str | None = None
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict."""
        return {
            "status": self.status,
            "docx_path": str(self.docx_path) if self.docx_path else None,
            "md_path": str(self.md_path) if self.md_path else None,
            "sections": self.sections,
            "refined": self.refined,
            "elapsed_seconds": self.elapsed_seconds,
            "error": self.error,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class InspectionResult:
    """Structural metadata for a Markdown file without full conversion."""

    file_path: Path
    line_count: int
    heading_count: int
    table_line_count: int
    section_count: int

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict."""
        return {
            "file_path": str(self.file_path),
            "line_count": self.line_count,
            "heading_count": self.heading_count,
            "table_line_count": self.table_line_count,
            "section_count": self.section_count,
        }

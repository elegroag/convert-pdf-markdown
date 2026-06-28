"""Application DTOs for XLSX2MD."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from xlsx2md.domain.value_objects.value_objects import ConversionConfig


@dataclass(frozen=True)
class ConversionRequest:
    """Public DTO for a single conversion request."""

    xlsx_path: Path
    output_dir: Path
    config: ConversionConfig | None = None


@dataclass(frozen=True)
class ConversionResult:
    """Public DTO for a single conversion result."""

    status: str
    sheet_outputs: tuple[Path, ...] = ()
    index_path: Path | None = None
    total_sheets: int = 0
    total_rows: int = 0
    total_images: int = 0
    elapsed_seconds: float = 0.0
    error: str | None = None
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict."""
        return {
            "status": self.status,
            "sheet_outputs": [str(path) for path in self.sheet_outputs],
            "index_path": str(self.index_path) if self.index_path else None,
            "total_sheets": self.total_sheets,
            "total_rows": self.total_rows,
            "total_images": self.total_images,
            "elapsed_seconds": self.elapsed_seconds,
            "error": self.error,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class InspectionResult:
    """Result of inspect — structure without full conversion."""

    file_path: Path
    total_sheets: int
    sheet_names: tuple[str, ...]
    non_empty_sheets: int
    total_rows: int
    total_images: int

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict."""
        return {
            "file_path": str(self.file_path),
            "total_sheets": self.total_sheets,
            "sheet_names": list(self.sheet_names),
            "non_empty_sheets": self.non_empty_sheets,
            "total_rows": self.total_rows,
            "total_images": self.total_images,
        }

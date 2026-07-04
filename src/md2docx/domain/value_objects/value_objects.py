"""Domain value objects for MD2DOCX."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ConversionConfig:
    """Configuration for a Markdown to DOCX conversion run."""

    assets_subdir: str = "assets"
    base_font: str = "Calibri"
    base_font_size_pt: int = 11
    table_max_cols: int = 10
    consolidate: bool = True
    insert_toc: bool = True
    clean_tables: bool = True
    refine_with_libreoffice: bool = True
    keep_artifacts: bool = False
    reference_docx: Path | None = None
    section_delimiter: str = "=" * 60
    combined_md_name: str = "MANUAL_COMPLETO.md"
    output_docx_name: str = "MANUAL_SISTEMA.docx"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return {
            "assets_subdir": self.assets_subdir,
            "base_font": self.base_font,
            "base_font_size_pt": self.base_font_size_pt,
            "table_max_cols": self.table_max_cols,
            "consolidate": self.consolidate,
            "insert_toc": self.insert_toc,
            "clean_tables": self.clean_tables,
            "refine_with_libreoffice": self.refine_with_libreoffice,
            "keep_artifacts": self.keep_artifacts,
            "reference_docx": str(self.reference_docx) if self.reference_docx else None,
            "section_delimiter": self.section_delimiter,
            "combined_md_name": self.combined_md_name,
            "output_docx_name": self.output_docx_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversionConfig:
        """Build a config from a dict, ignoring unknown keys."""
        ref = data.get("reference_docx")
        return cls(
            assets_subdir=str(data.get("assets_subdir", "assets")),
            base_font=str(data.get("base_font", "Calibri")),
            base_font_size_pt=int(data.get("base_font_size_pt", 11)),
            table_max_cols=int(data.get("table_max_cols", 10)),
            consolidate=bool(data.get("consolidate", True)),
            insert_toc=bool(data.get("insert_toc", True)),
            clean_tables=bool(data.get("clean_tables", True)),
            refine_with_libreoffice=bool(data.get("refine_with_libreoffice", True)),
            keep_artifacts=bool(data.get("keep_artifacts", False)),
            reference_docx=Path(ref) if ref else None,
            section_delimiter=str(data.get("section_delimiter", "=" * 60)),
            combined_md_name=str(data.get("combined_md_name", "MANUAL_COMPLETO.md")),
            output_docx_name=str(data.get("output_docx_name", "MANUAL_SISTEMA.docx")),
        )


@dataclass(frozen=True)
class BatchConfig:
    """Configuration for a batch conversion run."""

    workers: int = 2
    skip_on_error: bool = True
    report_file: str = "batch_report.json"
    config: ConversionConfig = field(default_factory=ConversionConfig)

    def __post_init__(self) -> None:
        if self.workers < 1:
            raise ValueError("workers must be >= 1")

"""Domain value objects for XLSX2MD."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConversionConfig:
    """Configuration for an XLSX to Markdown conversion run."""

    assets_subdir: str = "assets"
    frontmatter: bool = True
    extract_images: bool = True
    max_rows: int | None = None
    max_cols: int | None = None
    default_table_max_cols: int = 15
    detect_blocks: bool = True
    include_index: bool = True
    table_format: str = "github"
    skip_empty_sheets: bool = True
    code_fence: str = "```"
    date_format: str = "iso"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return {
            "assets_subdir": self.assets_subdir,
            "frontmatter": self.frontmatter,
            "extract_images": self.extract_images,
            "max_rows": self.max_rows,
            "max_cols": self.max_cols,
            "default_table_max_cols": self.default_table_max_cols,
            "detect_blocks": self.detect_blocks,
            "include_index": self.include_index,
            "table_format": self.table_format,
            "skip_empty_sheets": self.skip_empty_sheets,
            "code_fence": self.code_fence,
            "date_format": self.date_format,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversionConfig:
        """Build a config from a dict, ignoring unknown keys."""
        return cls(
            assets_subdir=str(data.get("assets_subdir", "assets")),
            frontmatter=bool(data.get("frontmatter", True)),
            extract_images=bool(data.get("extract_images", True)),
            max_rows=data.get("max_rows"),
            max_cols=data.get("max_cols"),
            default_table_max_cols=int(data.get("default_table_max_cols", 15)),
            detect_blocks=bool(data.get("detect_blocks", True)),
            include_index=bool(data.get("include_index", True)),
            table_format=str(data.get("table_format", "github")),
            skip_empty_sheets=bool(data.get("skip_empty_sheets", True)),
            code_fence=str(data.get("code_fence", "```")),
            date_format=str(data.get("date_format", "iso")),
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

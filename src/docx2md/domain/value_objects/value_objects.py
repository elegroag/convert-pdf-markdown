"""Domain value objects for DOCX2MD."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConversionConfig:
    """Configuration for a DOCX to Markdown conversion run."""

    assets_subdir: str = "assets"
    frontmatter: bool = True
    extract_images: bool = True
    extract_tables: bool = True
    convert_images_to_png: bool = True
    code_fence: str = "```"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return {
            "assets_subdir": self.assets_subdir,
            "frontmatter": self.frontmatter,
            "extract_images": self.extract_images,
            "extract_tables": self.extract_tables,
            "convert_images_to_png": self.convert_images_to_png,
            "code_fence": self.code_fence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversionConfig:
        """Build a config from a dict, ignoring unknown keys."""
        return cls(
            assets_subdir=str(data.get("assets_subdir", "assets")),
            frontmatter=bool(data.get("frontmatter", True)),
            extract_images=bool(data.get("extract_images", True)),
            extract_tables=bool(data.get("extract_tables", True)),
            convert_images_to_png=bool(data.get("convert_images_to_png", True)),
            code_fence=str(data.get("code_fence", "```")),
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

"""Domain value objects: page content, cells, configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pdf2md.domain.value_objects.enums import (
    ExtractorEngine,
    HeadingStyle,
    TableEngine,
)


@dataclass(frozen=True)
class ContentBlock:
    """A semantically-tagged block of text on a PDF page.

    Attributes:
        block_type: The semantic category of the block.
        text: The text content of the block.
        level: 1-6 for headings; 0 for other block types.
        font_size: Detected font size in points.
        is_bold: Whether the text appears in bold.
        bbox: Optional bounding box (x0, y0, x1, y1) in PDF units.
    """

    block_type: str
    text: str
    level: int = 0
    font_size: float = 0.0
    is_bold: bool = False
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class TableCell:
    """A single cell in an extracted table.

    Attributes:
        text: Cell text content (sanitized for Markdown).
        is_header: Whether the cell belongs to the header row.
    """

    text: str
    is_header: bool = False


@dataclass(frozen=True)
class PageContent:
    """Lightweight representation of a page's text content.

    Used when only the textual content is needed (e.g., for search or
    indexing) without the heavy image and table data.
    """

    page_number: int
    text: str
    blocks: tuple[ContentBlock, ...] = ()


@dataclass(frozen=True)
class Link:
    """A hyperlink extracted from a PDF page.

    Attributes:
        url: The target URL or anchor.
        text: The visible text of the link.
        page_number: The page on which the link appears.
        is_internal: True if the link points inside the same document.
    """

    url: str
    text: str
    page_number: int
    is_internal: bool = False


@dataclass(frozen=True)
class ConversionConfig:
    """Configuration for a PDF to Markdown conversion run.

    Attributes:
        image_min_size: Minimum dimension (px) below which images are skipped.
        extract_tables: Whether to extract tables.
        table_extractor: Engine to use for table extraction.
        extract_links: Whether to extract hyperlinks.
        frontmatter: Whether to emit YAML frontmatter from PDF metadata.
        extract_images: Whether to extract images.
        heading_style: Markdown heading style.
        code_fence: Fence marker for code blocks (``` or ~~~).
        assets_subdir: Subdirectory under the output dir for image assets.
    """

    image_min_size: int = 200
    extract_tables: bool = True
    table_extractor: TableEngine = TableEngine.PDFPLUMBER
    extract_links: bool = True
    frontmatter: bool = True
    extract_images: bool = True
    heading_style: HeadingStyle = HeadingStyle.ATX
    code_fence: str = "```"
    assets_subdir: str = "assets"
    emit_link_list: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return {
            "image_min_size": self.image_min_size,
            "extract_tables": self.extract_tables,
            "table_extractor": self.table_extractor.value,
            "extract_links": self.extract_links,
            "frontmatter": self.frontmatter,
            "extract_images": self.extract_images,
            "heading_style": self.heading_style.value,
            "code_fence": self.code_fence,
            "assets_subdir": self.assets_subdir,
            "emit_link_list": self.emit_link_list,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversionConfig:
        """Build a config from a dict, ignoring unknown keys."""
        return cls(
            image_min_size=int(data.get("image_min_size", 200)),
            extract_tables=bool(data.get("extract_tables", True)),
            table_extractor=TableEngine(
                str(data.get("table_extractor", "pdfplumber"))
            ),
            extract_links=bool(data.get("extract_links", True)),
            frontmatter=bool(data.get("frontmatter", True)),
            extract_images=bool(data.get("extract_images", True)),
            heading_style=HeadingStyle(str(data.get("heading_style", "atx"))),
            code_fence=str(data.get("code_fence", "```")),
            assets_subdir=str(data.get("assets_subdir", "assets")),
            emit_link_list=bool(data.get("emit_link_list", False)),
        )


@dataclass(frozen=True)
class BatchConfig:
    """Configuration for a batch conversion run."""

    workers: int = 2
    skip_on_error: bool = True
    report_file: str = "batch_report.json"
    pages_filter: str | None = None
    extractor: ExtractorEngine = ExtractorEngine.PYMUPDF
    config: ConversionConfig = field(default_factory=ConversionConfig)

    def __post_init__(self) -> None:
        if self.workers < 1:
            raise ValueError("workers must be >= 1")

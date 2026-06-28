"""Domain entities for XLSX2MD."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union


@dataclass(frozen=True)
class CellBlock:
    """A single spreadsheet cell ready for Markdown rendering."""

    value: str
    formula: str | None = None
    is_header: bool = False


@dataclass(frozen=True)
class ImageBlock:
    """Reference to an extracted image asset anchored to a cell."""

    filename: str
    alt_text: str = ""
    anchor_cell: str = ""


@dataclass
class TableBlock:
    """A tabular region detected inside a worksheet."""

    title: str = ""
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    anchor_start: str = ""
    anchor_end: str = ""

    def is_empty(self) -> bool:
        """Return True if the table has no data rows."""
        return not self.rows


@dataclass
class KeyValueBlock:
    """A label/value pair, e.g. ``OBJETIVO: <text>``."""

    label: str
    value: str
    anchor: str = ""


@dataclass
class HeadingBlock:
    """A standalone heading-like row inside the sheet narrative."""

    text: str
    anchor: str = ""


@dataclass
class ParagraphBlock:
    """A standalone paragraph of text inside the sheet narrative."""

    text: str
    anchor: str = ""


SheetBlock = Union["NarrativeSheet", "TableSheet", "ImageSheet", "EmptySheet"]


@dataclass
class NarrativeSheet:
    """A worksheet composed of narrative sections (no tabular regions)."""

    name: str
    index: int
    blocks: list[HeadingBlock | ParagraphBlock | KeyValueBlock | TableBlock] = field(default_factory=list)
    images: list[ImageBlock] = field(default_factory=list)
    raw_dimensions: str = ""

    def is_empty(self) -> bool:
        return not self.blocks and not self.images

    @property
    def row_count(self) -> int:
        return sum(
            len(block.rows) for block in self.blocks if isinstance(block, TableBlock)
        )


@dataclass
class TableSheet:
    """A worksheet dominated by a single tabular region."""

    name: str
    index: int
    tables: list[TableBlock] = field(default_factory=list)
    images: list[ImageBlock] = field(default_factory=list)
    raw_dimensions: str = ""

    def is_empty(self) -> bool:
        return not self.tables and not self.images

    @property
    def row_count(self) -> int:
        return sum(table.rows.__len__() for table in self.tables)


@dataclass
class ImageSheet:
    """A worksheet that mostly contains images."""

    name: str
    index: int
    caption: str = ""
    images: list[ImageBlock] = field(default_factory=list)
    raw_dimensions: str = ""

    def is_empty(self) -> bool:
        return not self.images

    @property
    def row_count(self) -> int:
        return 0


@dataclass
class EmptySheet:
    """A worksheet with no meaningful content."""

    name: str
    index: int
    raw_dimensions: str = ""

    def is_empty(self) -> bool:
        return True

    @property
    def row_count(self) -> int:
        return 0


@dataclass(frozen=True)
class XlsxMetadata:
    """Metadata extracted from an Excel workbook."""

    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""
    sheet_names: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        """Return True if no meaningful metadata is present."""
        return not any(
            getattr(self, field_name)
            for field_name in ("title", "author", "subject", "creator")
        )


@dataclass
class XlsxDocument:
    """Parsed contents of an Excel workbook."""

    file_path: Path
    sheets: list[SheetBlock] = field(default_factory=list)
    metadata: XlsxMetadata = field(default_factory=XlsxMetadata)


@dataclass
class MarkdownDocument:
    """Final Markdown document produced by a renderer."""

    source_xlsx: Path
    sheet_name: str
    content: str = ""
    assets_dir: Path | None = None
    output_path: Path | None = None
    frontmatter: str = ""

    def to_string(self) -> str:
        """Return the complete Markdown content."""
        chunks: list[str] = []
        if self.frontmatter:
            chunks.append(self.frontmatter)
        if self.content:
            chunks.append(self.content)
        return "\n\n".join(chunks) + "\n" if chunks else ""

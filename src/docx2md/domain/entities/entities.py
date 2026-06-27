"""Domain entities for DOCX2MD."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class HeadingBlock:
    """A heading with its level (1–9)."""

    level: int
    text: str


@dataclass(frozen=True)
class ParagraphBlock:
    """A paragraph with optional inline formatting flags."""

    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class ImageBlock:
    """Reference to an extracted image asset."""

    filename: str
    alt_text: str = ""


@dataclass
class TableBlock:
    """A table with rows and columns."""

    rows: list[list[str]] = field(default_factory=list)


@dataclass(frozen=True)
class ListItemBlock:
    """An ordered or unordered list item."""

    text: str
    ordered: bool = False
    level: int = 0


@dataclass(frozen=True)
class HorizontalRuleBlock:
    """A horizontal rule separator."""


DocumentBlock = (
    HeadingBlock
    | ParagraphBlock
    | ImageBlock
    | TableBlock
    | ListItemBlock
    | HorizontalRuleBlock
)


@dataclass
class DocxMetadata:
    """Metadata extracted from a Word document."""

    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""

    def is_empty(self) -> bool:
        """Return True if no meaningful metadata is present."""
        return not any(
            getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        )


@dataclass
class DocxDocument:
    """Parsed contents of a Word document."""

    file_path: Path
    blocks: list[DocumentBlock] = field(default_factory=list)
    metadata: DocxMetadata = field(default_factory=DocxMetadata)


@dataclass
class MarkdownDocument:
    """Final Markdown document produced by a renderer."""

    source_docx: Path
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
